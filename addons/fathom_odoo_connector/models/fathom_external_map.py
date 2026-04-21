from odoo import fields, models


class FathomExternalMap(models.Model):
    _name = 'fathom.external.map'
    _description = 'Fathom External ID Mapping'
    _order = 'write_date desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
    model = fields.Char(required=True, index=True)
    external_id = fields.Char(required=True, index=True)
    res_id = fields.Integer(required=True, index=True)
    checksum = fields.Char()
    source_updated_at = fields.Datetime()
    last_synced_at = fields.Datetime(default=fields.Datetime.now)

    _sql_constraints = [
        (
            'fathom_external_unique',
            'unique(model, external_id)',
            'Mapping already exists for this model and external ID.',
        ),
    ]

    def _compute_name(self):
        for rec in self:
            rec.name = f'{rec.model}:{rec.external_id}'
