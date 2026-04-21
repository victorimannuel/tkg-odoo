import hashlib
import json

from odoo import fields, models

from ..services.fathom_client import FathomApiClient


class FathomSync(models.AbstractModel):
    _name = 'fathom.sync'
    _description = 'Fathom Sync Service'

    def _is_enabled(self):
        config = self.env['ir.config_parameter'].sudo()
        return config.get_param('fathom_odoo_connector.sync_enabled') == 'True'

    def _last_sync(self):
        config = self.env['ir.config_parameter'].sudo()
        return config.get_param('fathom_odoo_connector.last_sync_at')

    def _set_last_sync(self, dt):
        self.env['ir.config_parameter'].sudo().set_param('fathom_odoo_connector.last_sync_at', dt)

    def _checksum(self, payload):
        normalized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def _upsert_mapping(self, model_name, external_id, res_id, payload, source_updated_at=None):
        checksum = self._checksum(payload)
        mapping = self.env['fathom.external.map'].search([
            ('model', '=', model_name),
            ('external_id', '=', external_id),
        ], limit=1)
        if mapping:
            changed = mapping.checksum != checksum
            mapping.write({
                'res_id': res_id,
                'checksum': checksum,
                'source_updated_at': source_updated_at,
                'last_synced_at': fields.Datetime.now(),
            })
            return 'updated' if changed else 'skipped'
        self.env['fathom.external.map'].create({
            'model': model_name,
            'external_id': external_id,
            'res_id': res_id,
            'checksum': checksum,
            'source_updated_at': source_updated_at,
            'last_synced_at': fields.Datetime.now(),
        })
        return 'created'

    def _log_start(self, sync_type, request_path=None, request_payload=None):
        return self.env['fathom.sync.log'].create({
            'name': f'Fathom {sync_type} sync',
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

    def _simulate_upsert_records(self, records, model_name):
        stats = {'created': 0, 'updated': 0, 'skipped': 0, 'failed': 0, 'retry': 0}
        for rec in records:
            external_id = str(rec.get('id') or '')
            if not external_id:
                stats['failed'] += 1
                continue
            result = self._upsert_mapping(
                model_name=model_name,
                external_id=external_id,
                res_id=0,
                payload=rec,
                source_updated_at=rec.get('updated_at'),
            )
            stats[result] += 1
        return stats

    def _sync(self, sync_type, path):
        if not self._is_enabled():
            return

        params = {}
        last_sync = self._last_sync()
        if last_sync:
            params['updated_since'] = last_sync

        log = self._log_start(sync_type=sync_type, request_path=path, request_payload=params)
        client = FathomApiClient(self.env)
        try:
            payload, status_code = client.request('GET', path, params=params)
            records = payload.get('data', []) if isinstance(payload, dict) else []
            stats = self._simulate_upsert_records(records, model_name=f'fathom.{sync_type}')
            final_status = 'success' if stats['failed'] == 0 else 'partial'
            self._set_last_sync(fields.Datetime.now())
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
        self._sync(sync_type='master_data', path='/master_data')

    def cron_sync_transactions(self):
        self._sync(sync_type='transactions', path='/transactions')
