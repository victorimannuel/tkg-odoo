from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fathom_api_base_url = fields.Char(
        string='Fathom API Base URL',
        config_parameter='fathom_odoo_connector.api_base_url',
        default='https://api.fathomhq.com/v1',
    )
    fathom_api_key = fields.Char(
        string='Fathom API Key',
        config_parameter='fathom_odoo_connector.api_key',
    )
    fathom_sync_enabled = fields.Boolean(
        string='Enable Fathom Sync',
        config_parameter='fathom_odoo_connector.sync_enabled',
        default=False,
    )
    fathom_last_sync_at = fields.Datetime(
        string='Last Sync At',
        config_parameter='fathom_odoo_connector.last_sync_at',
        readonly=True,
    )
