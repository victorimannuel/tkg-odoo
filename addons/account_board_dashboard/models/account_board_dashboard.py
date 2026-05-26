from odoo import api, fields, models, tools


class AccountBoardKpiSummary(models.Model):
    _name = "account.board.kpi.summary"
    _description = "Accounting Board KPI Summary"
    _auto = False
    _rec_name = "company_id"

    company_id = fields.Many2one("res.company", readonly=True)
    snapshot_date = fields.Date(readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)
    revenue_mtd = fields.Monetary(currency_field="currency_id", readonly=True)
    revenue_ytd = fields.Monetary(currency_field="currency_id", readonly=True)
    gross_profit_mtd = fields.Monetary(currency_field="currency_id", readonly=True)
    gross_profit_ytd = fields.Monetary(currency_field="currency_id", readonly=True)
    net_profit_mtd = fields.Monetary(currency_field="currency_id", readonly=True)
    net_profit_ytd = fields.Monetary(currency_field="currency_id", readonly=True)
    cash_balance = fields.Monetary(currency_field="currency_id", readonly=True)
    ar_open = fields.Monetary(currency_field="currency_id", readonly=True)
    ap_open = fields.Monetary(currency_field="currency_id", readonly=True)

    @api.model
    def get_dashboard_payload(self):
        company_pl_map = {}
        self.env.cr.execute(
            """
            SELECT
                aml.company_id,
                SUM(
                    CASE
                        WHEN aa.account_type = 'expense_direct_cost'
                         AND date_trunc('month', am.date) = date_trunc('month', CURRENT_DATE)
                        THEN aml.balance
                        ELSE 0
                    END
                ) AS cogs_mtd,
                SUM(
                    CASE
                        WHEN aa.account_type = 'expense_direct_cost'
                         AND am.date >= date_trunc('year', CURRENT_DATE)
                        THEN aml.balance
                        ELSE 0
                    END
                ) AS cogs_ytd,
                SUM(
                    CASE
                        WHEN aa.account_type IN ('expense', 'expense_other', 'expense_depreciation')
                         AND date_trunc('month', am.date) = date_trunc('month', CURRENT_DATE)
                        THEN aml.balance
                        ELSE 0
                    END
                ) AS opex_mtd,
                SUM(
                    CASE
                        WHEN aa.account_type IN ('expense', 'expense_other', 'expense_depreciation')
                         AND am.date >= date_trunc('year', CURRENT_DATE)
                        THEN aml.balance
                        ELSE 0
                    END
                ) AS opex_ytd
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            JOIN account_account aa ON aa.id = aml.account_id
            WHERE am.state = 'posted'
            GROUP BY aml.company_id
            """
        )
        for row in self.env.cr.dictfetchall():
            company_pl_map[row["company_id"]] = row

        company_bs_map = {}
        self.env.cr.execute(
            """
            SELECT
                aml.company_id,
                SUM(CASE WHEN aa.account_type LIKE 'asset_%' THEN aml.balance ELSE 0 END) AS total_assets,
                SUM(CASE WHEN aa.account_type LIKE 'liability_%' THEN -aml.balance ELSE 0 END) AS total_liabilities,
                SUM(CASE WHEN aa.account_type IN ('equity', 'equity_unaffected') THEN -aml.balance ELSE 0 END) AS total_equity
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            JOIN account_account aa ON aa.id = aml.account_id
            WHERE am.state = 'posted'
            GROUP BY aml.company_id
            """
        )
        for row in self.env.cr.dictfetchall():
            company_bs_map[row["company_id"]] = row

        summary_data = []
        for rec in self.search([], order="company_id"):
            pl_vals = company_pl_map.get(rec.company_id.id, {})
            bs_vals = company_bs_map.get(rec.company_id.id, {})
            summary_data.append(
                {
                    "company_id": rec.company_id.id,
                    "company_name": rec.company_id.display_name,
                    "parent_company_id": rec.company_id.parent_id.id or False,
                    "parent_company_name": rec.company_id.parent_id.display_name or False,
                    "currency_code": rec.currency_id.name or rec.company_id.currency_id.name,
                    "revenue_mtd": rec.revenue_mtd,
                    "revenue_ytd": rec.revenue_ytd,
                    "gross_profit_mtd": rec.gross_profit_mtd,
                    "gross_profit_ytd": rec.gross_profit_ytd,
                    "net_profit_mtd": rec.net_profit_mtd,
                    "net_profit_ytd": rec.net_profit_ytd,
                    "cogs_mtd": pl_vals.get("cogs_mtd", 0.0),
                    "cogs_ytd": pl_vals.get("cogs_ytd", 0.0),
                    "opex_mtd": pl_vals.get("opex_mtd", 0.0),
                    "opex_ytd": pl_vals.get("opex_ytd", 0.0),
                    "cash_balance": rec.cash_balance,
                    "ar_open": rec.ar_open,
                    "ap_open": rec.ap_open,
                    "total_assets": bs_vals.get("total_assets", 0.0),
                    "total_liabilities": bs_vals.get("total_liabilities", 0.0),
                    "total_equity": bs_vals.get("total_equity", 0.0),
                }
            )

        monthly_data = []
        monthly_recs = self.env["account.board.kpi.monthly"].search(
            [], order="company_id, month_start desc"
        )
        for rec in monthly_recs:
            monthly_data.append(
                {
                    "key": f"{rec.company_id.id}-{rec.month_start}",
                    "company_id": rec.company_id.id,
                    "company_name": rec.company_id.display_name,
                    "currency_code": rec.currency_id.name or rec.company_id.currency_id.name,
                    "month_start": rec.month_start,
                    "revenue": rec.revenue,
                    "gross_profit": rec.gross_profit,
                    "net_profit": rec.net_profit,
                }
            )

        aging_data = []
        aging_recs = self.env["account.board.aging"].search(
            [], order="company_id, partner_type, bucket"
        )
        for rec in aging_recs:
            aging_data.append(
                {
                    "key": f"{rec.company_id.id}-{rec.partner_type}-{rec.bucket}",
                    "company_id": rec.company_id.id,
                    "company_name": rec.company_id.display_name,
                    "currency_code": rec.currency_id.name or rec.company_id.currency_id.name,
                    "partner_type": rec.partner_type,
                    "bucket": rec.bucket,
                    "amount": rec.amount,
                }
            )

        # Monthly cash trend (for cash flow/runway indicators)
        self.env.cr.execute(
            """
            SELECT
                aml.company_id,
                date_trunc('month', am.date)::date AS month_start,
                rc.currency_id,
                COALESCE(SUM(aml.balance), 0.0) AS cash_balance
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            JOIN account_account aa ON aa.id = aml.account_id
            JOIN res_company rc ON rc.id = aml.company_id
            WHERE am.state = 'posted'
              AND aa.account_type = 'asset_cash'
              AND am.date >= (date_trunc('month', CURRENT_DATE) - INTERVAL '23 months')
            GROUP BY aml.company_id, date_trunc('month', am.date), rc.currency_id
            ORDER BY aml.company_id, month_start
            """
        )
        cash_monthly = []
        for row in self.env.cr.dictfetchall():
            currency = self.env["res.currency"].browse(row["currency_id"])
            company = self.env["res.company"].browse(row["company_id"])
            cash_monthly.append(
                {
                    "company_id": row["company_id"],
                    "company_name": company.display_name,
                    "month_start": row["month_start"],
                    "currency_code": currency.name or company.currency_id.name,
                    "cash_balance": row["cash_balance"],
                }
            )

        return {
            "summary": summary_data,
            "monthly": monthly_data,
            "aging": aging_data,
            "cash_monthly": cash_monthly,
        }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH companies AS (
                    SELECT rc.id AS company_id, rc.currency_id
                    FROM res_company rc
                ),
                pl AS (
                    SELECT
                        aml.company_id,
                        date_trunc('month', am.date)::date AS month_start,
                        SUM(
                            CASE
                                WHEN aa.account_type IN ('income', 'income_other')
                                    THEN -aml.balance
                                ELSE 0
                            END
                        ) AS revenue,
                        SUM(
                            CASE
                                WHEN aa.account_type = 'expense_direct_cost'
                                    THEN aml.balance
                                ELSE 0
                            END
                        ) AS direct_cost,
                        SUM(
                            CASE
                                WHEN aa.account_type IN ('expense', 'expense_other', 'expense_depreciation', 'expense_direct_cost')
                                    THEN aml.balance
                                ELSE 0
                            END
                        ) AS total_expense
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    JOIN account_account aa ON aa.id = aml.account_id
                    WHERE am.state = 'posted'
                    GROUP BY aml.company_id, date_trunc('month', am.date)
                ),
                p AS (
                    SELECT
                        pl.company_id,
                        SUM(CASE WHEN pl.month_start = date_trunc('month', CURRENT_DATE)::date THEN pl.revenue ELSE 0 END) AS revenue_mtd,
                        SUM(CASE WHEN pl.month_start >= date_trunc('year', CURRENT_DATE)::date THEN pl.revenue ELSE 0 END) AS revenue_ytd,
                        SUM(CASE WHEN pl.month_start = date_trunc('month', CURRENT_DATE)::date THEN (pl.revenue - pl.direct_cost) ELSE 0 END) AS gross_profit_mtd,
                        SUM(CASE WHEN pl.month_start >= date_trunc('year', CURRENT_DATE)::date THEN (pl.revenue - pl.direct_cost) ELSE 0 END) AS gross_profit_ytd,
                        SUM(CASE WHEN pl.month_start = date_trunc('month', CURRENT_DATE)::date THEN (pl.revenue - pl.total_expense) ELSE 0 END) AS net_profit_mtd,
                        SUM(CASE WHEN pl.month_start >= date_trunc('year', CURRENT_DATE)::date THEN (pl.revenue - pl.total_expense) ELSE 0 END) AS net_profit_ytd
                    FROM pl
                    GROUP BY pl.company_id
                ),
                cash AS (
                    SELECT
                        aml.company_id,
                        COALESCE(SUM(aml.balance), 0.0) AS cash_balance
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    JOIN account_account aa ON aa.id = aml.account_id
                    WHERE am.state = 'posted'
                      AND aa.account_type = 'asset_cash'
                    GROUP BY aml.company_id
                ),
                ar AS (
                    SELECT
                        aml.company_id,
                        COALESCE(SUM(aml.amount_residual), 0.0) AS ar_open
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    JOIN account_account aa ON aa.id = aml.account_id
                    WHERE am.state = 'posted'
                      AND aa.account_type = 'asset_receivable'
                      AND aml.amount_residual <> 0
                    GROUP BY aml.company_id
                ),
                ap AS (
                    SELECT
                        aml.company_id,
                        COALESCE(SUM(aml.amount_residual), 0.0) AS ap_open
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    JOIN account_account aa ON aa.id = aml.account_id
                    WHERE am.state = 'posted'
                      AND aa.account_type = 'liability_payable'
                      AND aml.amount_residual <> 0
                    GROUP BY aml.company_id
                )
                SELECT
                    c.company_id AS id,
                    c.company_id,
                    CURRENT_DATE AS snapshot_date,
                    c.currency_id,
                    COALESCE(p.revenue_mtd, 0.0) AS revenue_mtd,
                    COALESCE(p.revenue_ytd, 0.0) AS revenue_ytd,
                    COALESCE(p.gross_profit_mtd, 0.0) AS gross_profit_mtd,
                    COALESCE(p.gross_profit_ytd, 0.0) AS gross_profit_ytd,
                    COALESCE(p.net_profit_mtd, 0.0) AS net_profit_mtd,
                    COALESCE(p.net_profit_ytd, 0.0) AS net_profit_ytd,
                    COALESCE(cash.cash_balance, 0.0) AS cash_balance,
                    ABS(COALESCE(ar.ar_open, 0.0)) AS ar_open,
                    ABS(COALESCE(ap.ap_open, 0.0)) AS ap_open
                FROM companies c
                LEFT JOIN p ON p.company_id = c.company_id
                LEFT JOIN cash ON cash.company_id = c.company_id
                LEFT JOIN ar ON ar.company_id = c.company_id
                LEFT JOIN ap ON ap.company_id = c.company_id
            )
            """
        )


class AccountBoardKpiMonthly(models.Model):
    _name = "account.board.kpi.monthly"
    _description = "Accounting Board KPI Monthly"
    _auto = False
    _order = "month_start desc"

    company_id = fields.Many2one("res.company", readonly=True)
    month_start = fields.Date(readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)
    revenue = fields.Monetary(currency_field="currency_id", readonly=True)
    gross_profit = fields.Monetary(currency_field="currency_id", readonly=True)
    net_profit = fields.Monetary(currency_field="currency_id", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH monthly AS (
                    SELECT
                        aml.company_id,
                        date_trunc('month', am.date)::date AS month_start,
                        SUM(
                            CASE
                                WHEN aa.account_type IN ('income', 'income_other')
                                    THEN -aml.balance
                                ELSE 0
                            END
                        ) AS revenue,
                        SUM(
                            CASE
                                WHEN aa.account_type = 'expense_direct_cost'
                                    THEN aml.balance
                                ELSE 0
                            END
                        ) AS direct_cost,
                        SUM(
                            CASE
                                WHEN aa.account_type IN ('expense', 'expense_other', 'expense_depreciation', 'expense_direct_cost')
                                    THEN aml.balance
                                ELSE 0
                            END
                        ) AS total_expense
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    JOIN account_account aa ON aa.id = aml.account_id
                    WHERE am.state = 'posted'
                      AND am.date >= (date_trunc('month', CURRENT_DATE) - INTERVAL '23 months')
                    GROUP BY aml.company_id, date_trunc('month', am.date)
                )
                SELECT
                    ROW_NUMBER() OVER (ORDER BY m.company_id, m.month_start) AS id,
                    m.company_id,
                    m.month_start,
                    rc.currency_id,
                    m.revenue,
                    (m.revenue - m.direct_cost) AS gross_profit,
                    (m.revenue - m.total_expense) AS net_profit
                FROM monthly m
                JOIN res_company rc ON rc.id = m.company_id
            )
            """
        )


class AccountBoardAging(models.Model):
    _name = "account.board.aging"
    _description = "Accounting Board Aging"
    _auto = False

    company_id = fields.Many2one("res.company", readonly=True)
    partner_type = fields.Selection(
        [("receivable", "Receivable"), ("payable", "Payable")], readonly=True
    )
    bucket = fields.Selection(
        [
            ("not_due", "Not Due"),
            ("1_30", "1-30"),
            ("31_60", "31-60"),
            ("61_90", "61-90"),
            ("90_plus", "90+"),
        ],
        readonly=True,
    )
    amount = fields.Monetary(currency_field="currency_id", readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH base AS (
                    SELECT
                        aml.company_id,
                        CASE
                            WHEN aa.account_type = 'asset_receivable' THEN 'receivable'
                            ELSE 'payable'
                        END AS partner_type,
                        CASE
                            WHEN COALESCE((CURRENT_DATE - aml.date_maturity), 0) <= 0 THEN 'not_due'
                            WHEN (CURRENT_DATE - aml.date_maturity) BETWEEN 1 AND 30 THEN '1_30'
                            WHEN (CURRENT_DATE - aml.date_maturity) BETWEEN 31 AND 60 THEN '31_60'
                            WHEN (CURRENT_DATE - aml.date_maturity) BETWEEN 61 AND 90 THEN '61_90'
                            ELSE '90_plus'
                        END AS bucket,
                        ABS(aml.amount_residual) AS amount
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    JOIN account_account aa ON aa.id = aml.account_id
                    WHERE am.state = 'posted'
                      AND aa.account_type IN ('asset_receivable', 'liability_payable')
                      AND aml.amount_residual <> 0
                )
                SELECT
                    ROW_NUMBER() OVER (ORDER BY b.company_id, b.partner_type, b.bucket) AS id,
                    b.company_id,
                    b.partner_type,
                    b.bucket,
                    SUM(b.amount) AS amount,
                    rc.currency_id
                FROM base b
                JOIN res_company rc ON rc.id = b.company_id
                GROUP BY b.company_id, b.partner_type, b.bucket, rc.currency_id
            )
            """
        )
