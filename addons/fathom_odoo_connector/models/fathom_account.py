import json

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..services.fathom_client import FathomApiClient


class FathomAccount(models.Model):
    _name = 'fathom.account'
    _description = 'Fathom Account Connection'
    _order = 'active desc, id desc'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    user_id = fields.Many2one(
        'res.users',
        string='Odoo User',
        required=True,
        index=True,
        default=lambda self: self.env.user,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )

    api_base_url = fields.Char(required=True, default='https://api.fathom.ai/external/v1')
    api_key = fields.Char(required=True)

    sync_enabled = fields.Boolean(default=True)
    last_sync_at = fields.Datetime(readonly=True)
    meetings_last_sync_at = fields.Datetime(readonly=True)

    connection_tested_at = fields.Datetime(readonly=True)
    connection_test_status = fields.Selection(
        selection=[('never', 'Never'), ('ok', 'OK'), ('failed', 'Failed')],
        default='never',
        readonly=True,
    )
    connection_test_message = fields.Text(readonly=True)

    @staticmethod
    def _normalize_base_url(value):
        return (value or '').strip()

    @api.onchange('api_base_url')
    def _onchange_api_base_url(self):
        for rec in self:
            rec.api_base_url = self._normalize_base_url(rec.api_base_url)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'api_base_url' in vals:
                vals['api_base_url'] = self._normalize_base_url(vals.get('api_base_url'))
        return super().create(vals_list)

    def write(self, vals):
        if 'api_base_url' in vals:
            vals['api_base_url'] = self._normalize_base_url(vals.get('api_base_url'))
        return super().write(vals)

    def action_test_connection(self):
        self.ensure_one()
        if not self.api_key:
            raise UserError('API key is required.')

        client = FathomApiClient(self.env, account=self)
        try:
            payload, status_code = client.request(
                'GET',
                '/meetings',
                params={'limit': 1, 'include_summary': True, 'include_action_items': True},
            )
            msg = f'Connected (HTTP {status_code}).'
            self.write({
                'connection_tested_at': fields.Datetime.now(),
                'connection_test_status': 'ok',
                'connection_test_message': msg + '\n' + json.dumps(payload, default=str)[:2000],
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Fathom Connection',
                    'message': msg,
                    'type': 'success',
                    'sticky': False,
                },
            }
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.write({
                'connection_tested_at': fields.Datetime.now(),
                'connection_test_status': 'failed',
                'connection_test_message': str(exc),
            })
            raise UserError(f'Connection test failed: {exc}') from exc

    def action_sync_meeting_summaries(self):
        self.ensure_one()
        if not self.sync_enabled or not self.active:
            raise UserError('Sync is not enabled for this account.')

        service = self.env['fathom.sync'].with_user(self.user_id).with_company(self.company_id)
        account_user_env = service.env['fathom.account'].browse(self.id)
        service._sync_meetings(account=account_user_env)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Fathom Sync',
                'message': 'Meeting summaries sync started.',
                'type': 'success',
                'sticky': False,
            },
        }
