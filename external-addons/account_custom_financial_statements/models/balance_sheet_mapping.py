from odoo import fields, models


class BalanceSheetMapping(models.Model):
    _name = "custom.bs.mapping"
    _description = "Custom Balance Sheet Mapping"
    _order = "company_id, side, sequence, id"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    sequence = fields.Integer(default=10)
    side = fields.Selection(
        [("asset", "Assets"), ("liability", "Liabilities"), ("equity", "Equity")],
        required=True,
        default="asset",
    )
    line_mode = fields.Selection(
        [("accounts", "Accounts / Groups"), ("current_year_earnings", "Current Year Earnings")],
        required=True,
        default="accounts",
    )
    name = fields.Char(required=True)
    account_ids = fields.Many2many("account.account", string="Accounts")
    group_ids = fields.Many2many("account.group", string="Account Groups")
    active = fields.Boolean(default=True)

