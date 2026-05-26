from odoo import models


class GeneralLedgerReport(models.AbstractModel):
    _inherit = "report.account_financial_report.general_ledger"

    def _get_report_values(self, docids, data):
        res = super()._get_report_values(docids, data)

        totals = {
            "has_accounts": False,
            "init_debit": 0.0,
            "init_credit": 0.0,
            "init_balance": 0.0,
            "fin_debit": 0.0,
            "fin_credit": 0.0,
            "fin_balance": 0.0,
        }

        general_ledger = res.get("general_ledger", [])
        if general_ledger:
            totals["has_accounts"] = True
            for account in general_ledger:
                init_bal = account.get("init_bal", {})
                fin_bal = account.get("fin_bal", {})
                totals["init_debit"] += init_bal.get("debit", 0.0)
                totals["init_credit"] += init_bal.get("credit", 0.0)
                totals["init_balance"] += init_bal.get("balance", 0.0)
                totals["fin_debit"] += fin_bal.get("debit", 0.0)
                totals["fin_credit"] += fin_bal.get("credit", 0.0)
                totals["fin_balance"] += fin_bal.get("balance", 0.0)

        res["gl_totals"] = totals
        return res
