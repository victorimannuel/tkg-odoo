import json
import re
from html import escape

from odoo import fields, models


class FathomMeetingSummary(models.Model):
    _name = 'fathom.meeting.summary'
    _description = 'Fathom Meeting Summary'
    _order = 'meeting_start desc, id desc'

    name = fields.Char(required=True, index=True)
    account_id = fields.Many2one('fathom.account', required=True, index=True, ondelete='cascade')
    calendar_event_id = fields.Many2one('calendar.event', index=True, ondelete='set null')

    recording_id = fields.Char(required=True, index=True)
    meeting_url = fields.Char()
    share_url = fields.Char()

    meeting_start = fields.Datetime(index=True)
    meeting_end = fields.Datetime()
    source_created_at = fields.Datetime()

    summary_markdown = fields.Text()
    summary_html = fields.Html(compute='_compute_summary_html', sanitize=True)

    action_items_json = fields.Text()
    action_items_html = fields.Html(compute='_compute_action_items_html', sanitize=True)

    transcript_json = fields.Text()
    transcript_html = fields.Html(compute='_compute_transcript_html', sanitize=True)
    synced_at = fields.Datetime(readonly=True, index=True)

    _sql_constraints = [
        ('uniq_account_recording', 'unique(account_id, recording_id)', 'Recording ID must be unique per account.'),
    ]

    def _markdown_to_html_basic(self, markdown_text):
        if not markdown_text:
            return False
        def _inline(text):
            txt = escape(text or '')
            txt = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', txt)
            txt = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', txt)
            txt = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', txt)
            txt = re.sub(r'`([^`]+)`', r'<code>\1</code>', txt)
            return txt

        lines = (markdown_text or '').splitlines()
        out = []
        in_ul = False
        in_ol = False
        paragraph = []

        def flush_paragraph():
            if paragraph:
                out.append(f"<p>{_inline(' '.join(paragraph).strip())}</p>")
                paragraph.clear()

        def close_lists():
            nonlocal in_ul, in_ol
            if in_ul:
                out.append('</ul>')
                in_ul = False
            if in_ol:
                out.append('</ol>')
                in_ol = False

        for raw_line in lines:
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped:
                flush_paragraph()
                close_lists()
                continue

            h = re.match(r'^(#{1,6})\s+(.*)$', stripped)
            if h:
                flush_paragraph()
                close_lists()
                level = len(h.group(1))
                out.append(f"<h{level}>{_inline(h.group(2).strip())}</h{level}>")
                continue

            ul = re.match(r'^[-*]\s+(.*)$', stripped)
            if ul:
                flush_paragraph()
                if in_ol:
                    out.append('</ol>')
                    in_ol = False
                if not in_ul:
                    out.append('<ul>')
                    in_ul = True
                out.append(f"<li>{_inline(ul.group(1).strip())}</li>")
                continue

            ol = re.match(r'^\d+\.\s+(.*)$', stripped)
            if ol:
                flush_paragraph()
                if in_ul:
                    out.append('</ul>')
                    in_ul = False
                if not in_ol:
                    out.append('<ol>')
                    in_ol = True
                out.append(f"<li>{_inline(ol.group(1).strip())}</li>")
                continue

            close_lists()
            paragraph.append(stripped)

        flush_paragraph()
        close_lists()
        return '\n'.join(out) if out else False

    def _compute_summary_html(self):
        for rec in self:
            rec.summary_html = rec._markdown_to_html_basic(rec.summary_markdown)

    def _compute_action_items_html(self):
        for rec in self:
            rec.action_items_html = rec._action_items_json_to_html(rec.action_items_json)

    def _compute_transcript_html(self):
        for rec in self:
            rec.transcript_html = rec._transcript_json_to_html(rec.transcript_json)

    def _format_transcript_timestamp(self, seconds_value):
        try:
            total_seconds = int(float(seconds_value or 0))
        except Exception:  # pylint: disable=broad-exception-caught
            return ''
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours:
            return f'{hours}:{minutes:02d}:{seconds:02d}'
        return f'{minutes:02d}:{seconds:02d}'

    def _extract_transcript_lines(self, payload):
        lines = []
        if isinstance(payload, list):
            for item in payload:
                lines.extend(self._extract_transcript_lines(item))
            return lines

        if isinstance(payload, dict):
            speaker = item_speaker = payload.get('speaker') or payload.get('speaker_name')
            if isinstance(item_speaker, dict):
                speaker = item_speaker.get('name') or item_speaker.get('email')
            text = payload.get('text') or payload.get('content') or payload.get('utterance')
            start = payload.get('start') or payload.get('start_time') or payload.get('offset')
            if text:
                lines.append({
                    'speaker': str(speaker or 'Unknown'),
                    'text': str(text),
                    'timestamp': self._format_transcript_timestamp(start),
                })
                return lines
            for key in ('segments', 'items', 'data', 'transcript'):
                value = payload.get(key)
                if value:
                    lines.extend(self._extract_transcript_lines(value))
            return lines

        if isinstance(payload, str) and payload.strip():
            lines.append({'speaker': 'Transcript', 'text': payload.strip(), 'timestamp': ''})
        return lines

    def _transcript_json_to_html(self, transcript_json):
        if not transcript_json:
            return '<p>No transcript.</p>'
        try:
            payload = json.loads(transcript_json)
        except Exception:  # pylint: disable=broad-exception-caught
            return f'<pre>{escape(transcript_json)}</pre>'

        lines = self._extract_transcript_lines(payload)
        if not lines:
            return '<p>No transcript.</p>'

        rows = []
        for line in lines:
            speaker = escape(line.get('speaker') or 'Unknown')
            text = escape(line.get('text') or '')
            timestamp = escape(line.get('timestamp') or '')
            time_html = f'<small>[{timestamp}]</small> ' if timestamp else ''
            rows.append(f'<p>{time_html}<strong>{speaker}:</strong> {text}</p>')
        return ''.join(rows)

    def _action_items_json_to_html(self, action_items_json):
        if not action_items_json:
            return '<p>No action items.</p>'
        try:
            payload = json.loads(action_items_json)
        except Exception:  # pylint: disable=broad-exception-caught
            return f'<pre>{escape(action_items_json)}</pre>'

        if not isinstance(payload, list) or not payload:
            return '<p>No action items.</p>'

        items_html = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            description = escape(str(item.get('description') or '')).strip()
            if not description:
                continue
            completed = bool(item.get('completed'))
            assignee = item.get('assignee') or {}
            assignee_label = escape(str(assignee.get('name') or assignee.get('email') or '')).strip()
            playback_url = escape(str(item.get('recording_playback_url') or '')).strip()

            meta_bits = ['Done' if completed else 'Open']
            if assignee_label:
                meta_bits.append(f'Assignee: {assignee_label}')
            meta = ' | '.join(meta_bits)

            link = f' <a href="{playback_url}" target="_blank" rel="noopener noreferrer">Playback</a>' if playback_url else ''
            items_html.append(f'<li><strong>{description}</strong><br/><small>{escape(meta)}</small>{link}</li>')

        if not items_html:
            return False
        return '<ul>' + ''.join(items_html) + '</ul>'
