from odoo import fields, models


class FathomSyncLog(models.Model):
    _name = 'fathom.sync.log'
    _description = 'Fathom Sync Log'
    _order = 'create_date desc, id desc'

    name = fields.Char(required=True, default='Fathom Sync')
    sync_type = fields.Selection(
        selection=[
            ('master_data', 'Master Data'),
            ('transactions', 'Transactions'),
            ('manual', 'Manual'),
        ],
        required=True,
        default='manual',
    )
    status = fields.Selection(
        selection=[
            ('running', 'Running'),
            ('success', 'Success'),
            ('partial', 'Partial'),
            ('failed', 'Failed'),
        ],
        required=True,
        default='running',
    )
    request_path = fields.Char()
    request_payload = fields.Text()
    response_status = fields.Integer()
    response_body = fields.Text()
    error_message = fields.Text()
    created_count = fields.Integer(default=0)
    updated_count = fields.Integer(default=0)
    skipped_count = fields.Integer(default=0)
    failed_count = fields.Integer(default=0)
    retry_count = fields.Integer(default=0)
