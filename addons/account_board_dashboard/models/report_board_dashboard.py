from odoo import api, models


class ReportBoardDashboardPdf(models.AbstractModel):
    _name = "report.account_board_dashboard.report_board_dashboard_pdf"
    _description = "Board Dashboard PDF Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        period = self.env.context.get("board_period", "ytd")
        payload = self.env["account.board.kpi.summary"].get_dashboard_payload()

        summary = payload.get("summary", [])
        monthly = payload.get("monthly", [])
        aging = payload.get("aging", [])

        def total(key):
            return sum(float(rec.get(key) or 0.0) for rec in summary)

        headline = {
            "period": period.upper(),
            "revenue": total("revenue_mtd" if period == "mtd" else "revenue_ytd"),
            "net_profit": total("net_profit_mtd" if period == "mtd" else "net_profit_ytd"),
            "cash": total("cash_balance"),
            "ar": total("ar_open"),
            "ap": total("ap_open"),
            "currency": (summary[0].get("currency_code") if summary else "USD"),
        }
        headline["quick_ratio"] = ((abs(headline["cash"]) + abs(headline["ar"])) / abs(headline["ap"])) if headline["ap"] else 0.0

        key = "revenue_mtd" if period == "mtd" else "revenue_ytd"
        total_revenue = sum(max(0.0, float(rec.get(key) or 0.0)) for rec in summary)
        revenue_share = []
        for rec in sorted(summary, key=lambda r: float(r.get(key) or 0.0), reverse=True):
            value = max(0.0, float(rec.get(key) or 0.0))
            if not value:
                continue
            revenue_share.append({
                "company": rec.get("company_name"),
                "value": value,
                "pct": ((value / total_revenue) * 100.0) if total_revenue else 0.0,
                "currency": rec.get("currency_code") or "USD",
            })

        overdue_90 = sum(
            abs(float(row.get("amount") or 0.0))
            for row in aging
            if row.get("partner_type") == "receivable" and row.get("bucket") == "90_plus"
        )
        total_ar = abs(total("ar_open"))
        risks = {
            "overdue_90": overdue_90,
            "overdue_90_pct": (overdue_90 / total_ar * 100.0) if total_ar else 0.0,
            "currency": headline["currency"],
        }

        by_month = {}
        for row in monthly:
            month = row.get("month_start")
            if month not in by_month:
                by_month[month] = {
                    "month": month,
                    "currency": row.get("currency_code") or "USD",
                    "revenue": 0.0,
                    "gross_profit": 0.0,
                    "net_profit": 0.0,
                }
            by_month[month]["revenue"] += float(row.get("revenue") or 0.0)
            by_month[month]["gross_profit"] += float(row.get("gross_profit") or 0.0)
            by_month[month]["net_profit"] += float(row.get("net_profit") or 0.0)

        trend = []
        for month in sorted(by_month.keys())[-12:]:
            rec = by_month[month]
            revenue = rec["revenue"]
            rec["gross_margin_pct"] = (rec["gross_profit"] / revenue * 100.0) if revenue else 0.0
            rec["net_margin_pct"] = (rec["net_profit"] / revenue * 100.0) if revenue else 0.0
            trend.append(rec)

        return {
            "doc_ids": docids,
            "doc_model": "account.board.kpi.summary",
            "docs": self.env["account.board.kpi.summary"].search([]),
            "headline": headline,
            "revenue_share": revenue_share,
            "trend": trend,
            "risks": risks,
        }
