import json
from datetime import datetime, timedelta, timezone

from odoo import fields, models

from ..services.fathom_client import FathomApiClient


class FathomSync(models.AbstractModel):
    _name = 'fathom.sync'
    _description = 'Fathom Sync Service'

    def _log_start(self, sync_type, request_path=None, request_payload=None, account=None):
        return self.env['fathom.sync.log'].create({
            'name': f'Fathom {sync_type} sync',
            'account_id': account.id if account else False,
            'user_id': account.user_id.id if account else self.env.user.id,
            'sync_type': sync_type,
            'status': 'running',
            'request_path': request_path,
            'request_payload': json.dumps(request_payload, default=str) if request_payload else False,
        })

    def _log_finish(self, log, status, stats=None, response_status=None, response_body=None, error_message=None):
        stats = stats or {}
        log.write({
            'status': status,
            'created_count': stats.get('created', 0),
            'updated_count': stats.get('updated', 0),
            'skipped_count': stats.get('skipped', 0),
            'failed_count': stats.get('failed', 0),
            'retry_count': stats.get('retry', 0),
            'response_status': response_status,
            'response_body': json.dumps(response_body, default=str)[:64000] if response_body else False,
            'error_message': error_message,
        })

    def _to_utc_datetime(self, value):
        if not value:
            return False
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return False
            try:
                dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
            except Exception:  # pylint: disable=broad-exception-caught
                return False
            if getattr(dt, 'tzinfo', None):
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        if isinstance(value, datetime):
            if getattr(value, 'tzinfo', None):
                return value.astimezone(timezone.utc).replace(tzinfo=None)
            return value
        return False

    def _find_calendar_event_for_meeting(self, account, meeting, tolerance_minutes=15):
        debug = {
            'meeting_title': meeting.get('meeting_title') or meeting.get('title') or '',
            'scheduled_start_time': meeting.get('scheduled_start_time'),
            'scheduled_end_time': meeting.get('scheduled_end_time'),
            'tolerance_minutes': tolerance_minutes,
        }
        scheduled_start = self._to_utc_datetime(meeting.get('scheduled_start_time'))
        scheduled_end = self._to_utc_datetime(meeting.get('scheduled_end_time'))
        if not scheduled_start or not scheduled_end:
            debug['reason'] = 'missing_scheduled_time'
            return self.env['calendar.event'], debug

        title = debug['meeting_title']
        if not title:
            debug['reason'] = 'missing_title'
            return self.env['calendar.event'], debug
        start_min = scheduled_start - timedelta(minutes=tolerance_minutes)
        start_max = scheduled_start + timedelta(minutes=tolerance_minutes)
        end_min = scheduled_end - timedelta(minutes=tolerance_minutes)
        end_max = scheduled_end + timedelta(minutes=tolerance_minutes)

        domain = [
            ('start', '>=', fields.Datetime.to_string(start_min)),
            ('start', '<=', fields.Datetime.to_string(start_max)),
            ('stop', '>=', fields.Datetime.to_string(end_min)),
            ('stop', '<=', fields.Datetime.to_string(end_max)),
            ('name', 'ilike', title),
        ]

        candidates = self.env['calendar.event'].search(domain, limit=20)
        if not candidates:
            debug['reason'] = 'no_candidates'
            return candidates, debug

        def score(event):
            return abs((event.start - scheduled_start).total_seconds())

        best = candidates.sorted(key=score)[:1]
        debug['reason'] = 'matched' if best else 'no_best_candidate'
        debug['candidates'] = [
            {
                'id': event.id,
                'name': event.name,
                'start': fields.Datetime.to_string(event.start),
                'stop': fields.Datetime.to_string(event.stop),
            }
            for event in candidates
        ]
        if best:
            debug['matched_event'] = {
                'id': best.id,
                'name': best.name,
                'start': fields.Datetime.to_string(best.start),
                'stop': fields.Datetime.to_string(best.stop),
            }
        return best, debug

    def _extract_summary_markdown(self, payload):
        if isinstance(payload, str):
            return payload.strip() or False
        if isinstance(payload, dict):
            for key in (
                'markdown_formatted',
                'markdown',
                'summary',
                'summary_markdown',
                'summary_text',
                'text',
                'content',
                'body',
                'description',
            ):
                value = payload.get(key)
                if value:
                    extracted = self._extract_summary_markdown(value)
                    if extracted:
                        return extracted
            for key in ('data', 'result', 'items', 'recording', 'summary_data'):
                value = payload.get(key)
                if value:
                    extracted = self._extract_summary_markdown(value)
                    if extracted:
                        return extracted
        if isinstance(payload, list):
            for item in payload:
                extracted = self._extract_summary_markdown(item)
                if extracted:
                    return extracted
        return False

    def _extract_transcript_payload(self, payload):
        if isinstance(payload, str):
            return payload.strip() or False
        if isinstance(payload, dict):
            for key in ('transcript', 'items', 'data', 'segments', 'result'):
                value = payload.get(key)
                if value is not None:
                    extracted = self._extract_transcript_payload(value)
                    if extracted is not False:
                        return extracted
        if isinstance(payload, list):
            return payload
        return payload


    def _fetch_transcript(self, client, recording_id):
        transcript_payload, transcript_status = client.request(
            'GET',
            f'/recordings/{recording_id}/transcript',
        )
        return {
            'transcript_payload': transcript_payload,
            'transcript_status': transcript_status,
            'transcript_data': self._extract_transcript_payload(transcript_payload),
        }

    def _sync_meetings(self, account, limit=50):
        if not account or not account.sync_enabled or not account.active:
            return

        params = {
            'limit': limit,
            'include_summary': True,
            'include_action_items': True,
        }
        last_sync = account.meetings_last_sync_at
        if last_sync:
            buffered = fields.Datetime.to_datetime(last_sync) - timedelta(hours=2)
            params['created_since'] = fields.Datetime.to_string(buffered)

        log = self._log_start(sync_type='meetings', request_path='/meetings', request_payload=params, account=account)
        client = FathomApiClient(self.env, account=account)
        stats = {'created': 0, 'updated': 0, 'skipped': 0, 'failed': 0, 'retry': 0}
        newest_created_at = False

        try:
            payload, status_code = client.request('GET', '/meetings', params=params)
            items = payload.get('items', []) if isinstance(payload, dict) else []
            for meeting in items:
                recording_id = str(meeting.get('recording_id') or '')
                if not recording_id:
                    stats['failed'] += 1
                    continue

                summary = self.env['fathom.meeting.summary'].search([
                    ('account_id', '=', account.id),
                    ('recording_id', '=', recording_id),
                ], limit=1)
                if summary and summary.calendar_event_id:
                    event = summary.calendar_event_id
                    match_debug = {'reason': 'existing_summary_link', 'event_id': event.id}
                    log.match_debug = json.dumps(match_debug, default=str)
                else:
                    event, match_debug = self._find_calendar_event_for_meeting(account=account, meeting=meeting)
                    if match_debug:
                        log.match_debug = json.dumps(match_debug, default=str)
                    if not event:
                        # Log that we couldn't match an event, but still proceed to create the summary
                        log.match_debug = json.dumps(match_debug, default=str)
                    
                transcript_details = self._fetch_transcript(client, recording_id)
                action_items = meeting.get('action_items') or []
                summary_markdown = self._extract_summary_markdown(meeting.get('default_summary') or meeting.get('summary'))
                summary_vals = {
                    'name': meeting.get('meeting_title') or meeting.get('title') or (event.name if event else False) or recording_id,
                    'account_id': account.id,
                    'calendar_event_id': event.id if event else False,
                    'recording_id': recording_id,
                    'meeting_url': meeting.get('url'),
                    'share_url': meeting.get('share_url'),
                    'meeting_start': self._to_utc_datetime(meeting.get('scheduled_start_time')) or (event.start if event else False),
                    'meeting_end': self._to_utc_datetime(meeting.get('scheduled_end_time')) or (event.stop if event else False),
                    'source_created_at': self._to_utc_datetime(meeting.get('created_at')),
                    'summary_markdown': summary_markdown,
                    'action_items_json': json.dumps(action_items, default=str),
                    'transcript_json': json.dumps(transcript_details.get('transcript_data') or [], default=str),
                    'synced_at': fields.Datetime.now(),
                }
                if summary:
                    summary.write(summary_vals)
                    stats['updated'] += 1
                else:
                    summary = self.env['fathom.meeting.summary'].create(summary_vals)
                    stats['created'] += 1
                if event:
                    event.write({'fathom_meeting_summary_id': summary.id})

                created_at = self._to_utc_datetime(meeting.get('created_at'))
                if created_at and (not newest_created_at or created_at > newest_created_at):
                    newest_created_at = created_at

            if newest_created_at:
                account.sudo().write({'meetings_last_sync_at': newest_created_at})

            final_status = 'success' if stats['failed'] == 0 else 'partial'
            self._log_finish(
                log,
                final_status,
                stats=stats,
                response_status=status_code,
                response_body=payload,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._log_finish(log, 'failed', stats=stats, error_message=str(exc))

    def _simulate_upsert_records(self, records):
        stats = {'created': 0, 'updated': 0, 'skipped': 0, 'failed': 0, 'retry': 0}
        for rec in records:
            external_id = str(rec.get('id') or '')
            if not external_id:
                stats['failed'] += 1
                continue
            stats['skipped'] += 1
        return stats

    def _sync(self, sync_type, path, account):
        if not account or not account.sync_enabled or not account.active:
            return

        params = {}
        last_sync = account.last_sync_at
        if last_sync:
            params['updated_since'] = last_sync

        log = self._log_start(sync_type=sync_type, request_path=path, request_payload=params, account=account)
        client = FathomApiClient(self.env, account=account)
        try:
            payload, status_code = client.request('GET', path, params=params)
            records = payload.get('data', []) if isinstance(payload, dict) else []
            stats = self._simulate_upsert_records(records)
            final_status = 'success' if stats['failed'] == 0 else 'partial'
            account.sudo().write({'last_sync_at': fields.Datetime.now()})
            self._log_finish(
                log,
                final_status,
                stats=stats,
                response_status=status_code,
                response_body=payload,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._log_finish(log, 'failed', error_message=str(exc))

    def cron_sync_master_data(self):
        accounts = self.env['fathom.account'].sudo().search([('sync_enabled', '=', True), ('active', '=', True)])
        for account in accounts:
            service = self.with_user(account.user_id).with_company(account.company_id)
            account_user_env = service.env['fathom.account'].browse(account.id)
            service._sync(sync_type='master_data', path='/master_data', account=account_user_env)

    def cron_sync_transactions(self):
        accounts = self.env['fathom.account'].sudo().search([('sync_enabled', '=', True), ('active', '=', True)])
        for account in accounts:
            service = self.with_user(account.user_id).with_company(account.company_id)
            account_user_env = service.env['fathom.account'].browse(account.id)
            service._sync(sync_type='transactions', path='/transactions', account=account_user_env)

    def cron_sync_meeting_summaries(self):
        accounts = self.env['fathom.account'].sudo().search([('sync_enabled', '=', True), ('active', '=', True)])
        for account in accounts:
            service = self.with_user(account.user_id).with_company(account.company_id)
            account_user_env = service.env['fathom.account'].browse(account.id)
            service._sync_meetings(account=account_user_env)
