from odoo import api, models
from odoo.tools import date_utils


class FinancialStatementService(models.AbstractModel):
    _name = "custom.financial.statement.service"
    _description = "Custom Financial Statement Service"

    @api.model
    def _base_domain(self, company_id, target_move, date_from=False, date_to=False):
        domain = [
            ("company_id", "=", company_id),
            ("display_type", "not in", ["line_note", "line_section"]),
        ]
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))
        if target_move == "posted":
            domain.append(("move_id.state", "=", "posted"))
        else:
            domain.append(("move_id.state", "in", ["draft", "posted"]))
        return domain

    @api.model
    def _amount_abs_credit_nature(self, amount):
        return -amount

    @api.model
    def _sum_by_types(self, company_id, target_move, date_from, date_to, account_types):
        domain = self._base_domain(
            company_id, target_move, date_from=date_from, date_to=date_to
        )
        domain.append(("account_id.account_type", "in", account_types))
        grouped = self.env["account.move.line"].read_group(
            domain=domain,
            fields=["balance:sum", "account_id"],
            groupby=["account_id"],
            lazy=False,
        )
        data = {k: 0.0 for k in account_types}
        for row in grouped:
            account = self.env["account.account"].browse(row["account_id"][0])
            if account.account_type in data:
                data[account.account_type] += row.get("balance", 0.0)
        return data

    @api.model
    def _detail_by_types(self, company_id, target_move, date_from, date_to, account_types):
        domain = self._base_domain(
            company_id, target_move, date_from=date_from, date_to=date_to
        )
        domain.append(("account_id.account_type", "in", account_types))
        grouped = self.env["account.move.line"].read_group(
            domain=domain,
            fields=["balance:sum", "account_id"],
            groupby=["account_id"],
            lazy=False,
        )
        details = {key: [] for key in account_types}
        accounts = self.env["account.account"].browse(
            [row["account_id"][0] for row in grouped if row.get("account_id")]
        )
        accounts_by_id = {account.id: account for account in accounts}
        for row in grouped:
            account_id = row.get("account_id") and row["account_id"][0]
            account = accounts_by_id.get(account_id)
            if not account or account.account_type not in details:
                continue
            amount = row.get("balance", 0.0)
            if account.account_type in {"income", "income_other"}:
                amount = self._amount_abs_credit_nature(amount)
            details[account.account_type].append(
                {
                    "code": account.code,
                    "name": account.name,
                    "label": f"{account.code} - {account.name}",
                    "amount": amount,
                }
            )
        for key in details:
            details[key] = sorted(details[key], key=lambda item: item["code"] or "")
        return details

    @api.model
    def get_profit_and_loss(self, company_id, date_from, date_to, target_move):
        income_types = ["income", "income_other"]
        expense_types = ["expense", "expense_depreciation", "expense_direct_cost"]
        raw = self._sum_by_types(
            company_id=company_id,
            target_move=target_move,
            date_from=date_from,
            date_to=date_to,
            account_types=income_types + expense_types,
        )
        details = self._detail_by_types(
            company_id=company_id,
            target_move=target_move,
            date_from=date_from,
            date_to=date_to,
            account_types=income_types + expense_types,
        )

        revenue = self._amount_abs_credit_nature(
            raw.get("income", 0.0)
        ) + self._amount_abs_credit_nature(raw.get("income_other", 0.0))
        expenses = (
            raw.get("expense", 0.0)
            + raw.get("expense_depreciation", 0.0)
            + raw.get("expense_direct_cost", 0.0)
        )
        net_profit = revenue - expenses

        sections = [
            {
                "label": "Operating Revenue",
                "amount": self._amount_abs_credit_nature(raw.get("income", 0.0)),
                "lines": details.get("income", []),
            },
            {
                "label": "Other Revenue",
                "amount": self._amount_abs_credit_nature(raw.get("income_other", 0.0)),
                "lines": details.get("income_other", []),
            },
            {
                "label": "Operating Expense",
                "amount": raw.get("expense", 0.0),
                "lines": details.get("expense", []),
            },
            {
                "label": "Depreciation Expense",
                "amount": raw.get("expense_depreciation", 0.0),
                "lines": details.get("expense_depreciation", []),
            },
            {
                "label": "Direct Cost",
                "amount": raw.get("expense_direct_cost", 0.0),
                "lines": details.get("expense_direct_cost", []),
            },
        ]

        return {
            "sections": sections,
            "total_revenue": revenue,
            "total_expense": expenses,
            "net_profit": net_profit,
        }

    @api.model
    def _current_year_earnings(self, company_id, date_to, target_move):
        company = self.env["res.company"].browse(company_id)
        fy_start, _fy_end = date_utils.get_fiscal_year(
            date_to,
            day=company.fiscalyear_last_day,
            month=int(company.fiscalyear_last_month),
        )
        pnl = self.get_profit_and_loss(company_id, fy_start, date_to, target_move)
        return pnl["net_profit"]

    @api.model
    def get_balance_sheet(self, company_id, date_to, target_move):
        asset_types = [
            "asset_receivable",
            "asset_cash",
            "asset_current",
            "asset_non_current",
            "asset_prepayments",
            "asset_fixed",
        ]
        liability_types = ["liability_payable", "liability_credit_card", "liability_current", "liability_non_current"]
        equity_types = ["equity", "equity_unaffected"]

        raw_assets = self._sum_by_types(
            company_id=company_id,
            target_move=target_move,
            date_from=False,
            date_to=date_to,
            account_types=asset_types,
        )
        raw_liabilities = self._sum_by_types(
            company_id=company_id,
            target_move=target_move,
            date_from=False,
            date_to=date_to,
            account_types=liability_types,
        )
        raw_equity = self._sum_by_types(
            company_id=company_id,
            target_move=target_move,
            date_from=False,
            date_to=date_to,
            account_types=equity_types,
        )
        asset_details = self._detail_by_types(
            company_id=company_id,
            target_move=target_move,
            date_from=False,
            date_to=date_to,
            account_types=asset_types,
        )
        liability_details = self._detail_by_types(
            company_id=company_id,
            target_move=target_move,
            date_from=False,
            date_to=date_to,
            account_types=liability_types,
        )
        equity_details = self._detail_by_types(
            company_id=company_id,
            target_move=target_move,
            date_from=False,
            date_to=date_to,
            account_types=equity_types,
        )

        assets_total = sum(raw_assets.values())
        liabilities_total = self._amount_abs_credit_nature(sum(raw_liabilities.values()))
        equity_total = self._amount_abs_credit_nature(sum(raw_equity.values()))
        current_year_earnings = self._current_year_earnings(
            company_id, date_to, target_move
        )
        total_equity = equity_total + current_year_earnings
        liab_equity_total = liabilities_total + total_equity

        return {
            "asset_sections": [
                {
                    "label": "Receivables",
                    "amount": raw_assets.get("asset_receivable", 0.0),
                    "lines": asset_details.get("asset_receivable", []),
                },
                {
                    "label": "Cash and Bank",
                    "amount": raw_assets.get("asset_cash", 0.0),
                    "lines": asset_details.get("asset_cash", []),
                },
                {
                    "label": "Current Assets",
                    "amount": raw_assets.get("asset_current", 0.0),
                    "lines": asset_details.get("asset_current", []),
                },
                {
                    "label": "Prepayments",
                    "amount": raw_assets.get("asset_prepayments", 0.0),
                    "lines": asset_details.get("asset_prepayments", []),
                },
                {
                    "label": "Fixed Assets",
                    "amount": raw_assets.get("asset_fixed", 0.0),
                    "lines": asset_details.get("asset_fixed", []),
                },
                {
                    "label": "Non-current Assets",
                    "amount": raw_assets.get("asset_non_current", 0.0),
                    "lines": asset_details.get("asset_non_current", []),
                },
            ],
            "liability_sections": [
                {
                    "label": "Payables",
                    "amount": self._amount_abs_credit_nature(
                        raw_liabilities.get("liability_payable", 0.0)
                    ),
                    "lines": liability_details.get("liability_payable", []),
                },
                {
                    "label": "Credit Cards",
                    "amount": self._amount_abs_credit_nature(
                        raw_liabilities.get("liability_credit_card", 0.0)
                    ),
                    "lines": liability_details.get("liability_credit_card", []),
                },
                {
                    "label": "Current Liabilities",
                    "amount": self._amount_abs_credit_nature(
                        raw_liabilities.get("liability_current", 0.0)
                    ),
                    "lines": liability_details.get("liability_current", []),
                },
                {
                    "label": "Non-current Liabilities",
                    "amount": self._amount_abs_credit_nature(
                        raw_liabilities.get("liability_non_current", 0.0)
                    ),
                    "lines": liability_details.get("liability_non_current", []),
                },
            ],
            "equity_sections": [
                {
                    "label": "Equity",
                    "amount": self._amount_abs_credit_nature(raw_equity.get("equity", 0.0)),
                    "lines": equity_details.get("equity", []),
                },
                {
                    "label": "Unallocated Earnings",
                    "amount": self._amount_abs_credit_nature(
                        raw_equity.get("equity_unaffected", 0.0)
                    ),
                    "lines": equity_details.get("equity_unaffected", []),
                },
                {
                    "label": "Current Year Earnings",
                    "amount": current_year_earnings,
                    "lines": [],
                },
            ],
            "total_assets": assets_total,
            "total_liabilities": liabilities_total,
            "total_equity": total_equity,
            "total_liabilities_equity": liab_equity_total,
            "difference": assets_total - liab_equity_total,
        }
