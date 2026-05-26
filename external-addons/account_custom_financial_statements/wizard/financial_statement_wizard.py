from odoo import fields, models


class FinancialStatementWizard(models.TransientModel):
    _name = "custom.financial.statement.wizard"
    _description = "Custom Financial Statement Wizard"

    report_type = fields.Selection(
        [("pl", "Profit and Loss"), ("bs", "Balance Sheet")],
        required=True,
        default="pl",
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    date_from = fields.Date(default=lambda self: fields.Date.start_of(fields.Date.today(), "year"))
    date_to = fields.Date(required=True, default=fields.Date.today)
    target_move = fields.Selection(
        [("posted", "All Posted Entries"), ("all", "All Entries")],
        required=True,
        default="posted",
    )

    def action_print_html(self):
        self.ensure_one()
        report_name = (
            "account_custom_financial_statements.report_profit_loss"
            if self.report_type == "pl"
            else "account_custom_financial_statements.report_balance_sheet"
        )
        return self.env.ref(report_name).report_action(self)

    def action_print_pdf(self):
        self.ensure_one()
        report_name = (
            "account_custom_financial_statements.report_profit_loss_pdf"
            if self.report_type == "pl"
            else "account_custom_financial_statements.report_balance_sheet_pdf"
        )
        return self.env.ref(report_name).report_action(self)
