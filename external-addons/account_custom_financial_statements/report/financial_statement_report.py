from odoo import api, models


class ReportProfitLoss(models.AbstractModel):
    _name = "report.account_custom_financial_statements.pl"
    _description = "Profit and Loss Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["custom.financial.statement.wizard"].browse(docids)
        docs.ensure_one()
        service = self.env["custom.financial.statement.service"]
        payload = service.get_profit_and_loss(
            company_id=docs.company_id.id,
            date_from=docs.date_from,
            date_to=docs.date_to,
            target_move=docs.target_move,
        )
        return {
            "doc_ids": docs.ids,
            "doc_model": "custom.financial.statement.wizard",
            "docs": docs,
            "currency": docs.company_id.currency_id,
            "data": payload,
        }


class ReportBalanceSheet(models.AbstractModel):
    _name = "report.account_custom_financial_statements.bs"
    _description = "Balance Sheet Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["custom.financial.statement.wizard"].browse(docids)
        docs.ensure_one()
        service = self.env["custom.financial.statement.service"]
        payload = service.get_balance_sheet(
            company_id=docs.company_id.id,
            date_to=docs.date_to,
            target_move=docs.target_move,
        )
        return {
            "doc_ids": docs.ids,
            "doc_model": "custom.financial.statement.wizard",
            "docs": docs,
            "currency": docs.company_id.currency_id,
            "data": payload,
        }
