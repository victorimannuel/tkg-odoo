from odoo import fields, models


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    fathom_meeting_summary_id = fields.Many2one('fathom.meeting.summary', index=True, readonly=True, ondelete='set null')

    fathom_account_id = fields.Many2one(related='fathom_meeting_summary_id.account_id', store=True, readonly=True)
    fathom_recording_id = fields.Char(related='fathom_meeting_summary_id.recording_id', store=True, readonly=True)
    fathom_meeting_url = fields.Char(related='fathom_meeting_summary_id.meeting_url', store=True, readonly=True)
    fathom_share_url = fields.Char(related='fathom_meeting_summary_id.share_url', store=True, readonly=True)

    fathom_summary_markdown = fields.Text(related='fathom_meeting_summary_id.summary_markdown', store=True, readonly=True)
    fathom_summary_html = fields.Html(related='fathom_meeting_summary_id.summary_html', store=False, readonly=True)
    fathom_action_items_json = fields.Text(related='fathom_meeting_summary_id.action_items_json', store=True, readonly=True)
    fathom_action_items_html = fields.Html(related='fathom_meeting_summary_id.action_items_html', store=False, readonly=True)
    fathom_transcript_json = fields.Text(related='fathom_meeting_summary_id.transcript_json', store=True, readonly=True)

    fathom_synced_at = fields.Datetime(related='fathom_meeting_summary_id.synced_at', store=True, readonly=True)
