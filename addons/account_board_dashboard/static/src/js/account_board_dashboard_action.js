/** @odoo-module */

import { registry } from "@web/core/registry";
import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class AccountBoardDashboardAction extends Component {
    static template = "account_board_dashboard.AccountBoardDashboardAction";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this._patchedContainers = [];
        this._wheelHandler = null;
        this._scrollHost = null;
        this.rawData = null;

        this.state = useState({
            loading: true,
            error: null,
            data: null,
            selectedPeriod: "ytd",
            refreshedAt: null,
            snapshotDate: null,
            darkMode: false,
            headlineKpis: [],
            kpiDeltas: {},
            trendRows: [],
            trendSparkline: [],
            revenueShareChart: null,
            riskHighlights: [],
            whatChanged: [],
            decisionPanel: [],
            profitabilityRanking: [],
            auditability: null,
            benchmarking: [],
            agingBucketTotals: [],
            cashRunway: null,
            multiCurrencyWarning: null,
            profitWaterfall: null,
        });

        onWillStart(async () => {
            await this.loadData();
        });

        onMounted(() => {
            const root = this.el;
            if (!root) return;
            const candidates = [
                root.closest(".o_content"),
                root.closest(".o_action"),
                root.closest(".o_action_manager"),
            ].filter(Boolean);

            for (const el of candidates) {
                this._patchedContainers.push({
                    el,
                    overflowY: el.style.overflowY,
                    overflowX: el.style.overflowX,
                    height: el.style.height,
                    maxHeight: el.style.maxHeight,
                });
                el.style.overflowY = "auto";
                el.style.overflowX = "hidden";
            }

            this._scrollHost = root.querySelector(".o_account_board_dashboard_root") || root;
            this._wheelHandler = (ev) => {
                if (!this._scrollHost) return;
                this._scrollHost.scrollTop += ev.deltaY;
                ev.preventDefault();
            };
            this._scrollHost.addEventListener("wheel", this._wheelHandler, { passive: false });
        });

        onWillUnmount(() => {
            if (this._scrollHost && this._wheelHandler) {
                this._scrollHost.removeEventListener("wheel", this._wheelHandler);
            }
            for (const item of this._patchedContainers) {
                item.el.style.overflowY = item.overflowY;
                item.el.style.overflowX = item.overflowX;
                item.el.style.height = item.height;
                item.el.style.maxHeight = item.maxHeight;
            }
        });
    }

    async loadData() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const data = await this.orm.call("account.board.kpi.summary", "get_dashboard_payload", []);
            this.rawData = data;
            this.state.data = data;
            this.state.snapshotDate = (data.summary || [])[0]?.snapshot_date || null;
            this.state.refreshedAt = new Date().toISOString();
            this.recomputeDashboard();
        } catch (error) {
            this.state.error = error.message || "Failed to load dashboard data";
        } finally {
            this.state.loading = false;
        }
    }

    onChangePeriod(period) {
        this.state.selectedPeriod = period;
        this.recomputeDashboard();
    }

    async onRefreshData() {
        await this.loadData();
    }

    toggleDarkMode() {
        this.state.darkMode = !this.state.darkMode;
    }

    toggleFullScreen() {
        const root = this.el?.querySelector(".o_account_board_dashboard_root");
        if (!root) return;
        if (!document.fullscreenElement) {
            root.requestFullscreen?.();
        } else {
            document.exitFullscreen?.();
        }
    }

    recomputeDashboard() {
        const data = this.rawData || { summary: [], monthly: [], aging: [], cash_monthly: [] };
        const summary = data.summary || [];
        const monthly = data.monthly || [];
        const aging = data.aging || [];
        const cashMonthly = data.cash_monthly || [];

        this.state.multiCurrencyWarning = this.buildMultiCurrencyWarning(summary);
        this.state.headlineKpis = this.buildHeadlineKpis(summary);
        this.state.trendRows = this.buildConsolidatedTrend(monthly);
        this.state.trendSparkline = this.state.trendRows.map((r) => Number(r.revenue || 0));
        this.state.kpiDeltas = this.buildKpiDeltas(this.state.trendRows);
        this.state.revenueShareChart = this.buildRevenueShareChart(summary, this.state.selectedPeriod);
        this.state.profitWaterfall = this.buildProfitWaterfall(summary);
        this.state.riskHighlights = this.buildRiskHighlights(aging, summary);
        this.state.agingBucketTotals = this.buildAgingBucketTotals(aging);
        this.state.whatChanged = this.buildWhatChanged(summary, monthly, aging);
        this.state.profitabilityRanking = this.buildProfitabilityRanking(summary);
        this.state.decisionPanel = this.buildDecisionPanel(this.state.riskHighlights, this.state.profitabilityRanking);
        this.state.auditability = this.buildAuditability(summary, monthly, aging);
        this.state.benchmarking = this.buildBenchmarking(summary, monthly, aging);
        this.state.cashRunway = this.buildCashRunway(summary, cashMonthly);
    }

    formatCurrency(amount, currencyCode) {
        const value = Number(amount || 0);
        const code = currencyCode || "USD";
        return new Intl.NumberFormat(undefined, { style: "currency", currency: code, maximumFractionDigits: 2 }).format(value);
    }

    formatLabel(value) {
        const labels = {
            receivable: "Receivable",
            payable: "Payable",
            not_due: "Not Due",
            "1_30": "1-30",
            "31_60": "31-60",
            "61_90": "61-90",
            "90_plus": "90+",
        };
        return labels[value] || value || "-";
    }

    buildHeadlineKpis(summary) {
        if (!summary.length) return [];
        const currencyCode = summary[0].currency_code || "USD";
        const isMtd = this.state.selectedPeriod === "mtd";
        const daysYtd = Math.max(1, Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 1).getTime()) / 86400000) + 1);
        const revenue = summary.reduce((a, s) => a + Number(isMtd ? s.revenue_mtd || 0 : s.revenue_ytd || 0), 0);
        const grossProfit = summary.reduce((a, s) => a + Number(isMtd ? s.gross_profit_mtd || 0 : s.gross_profit_ytd || 0), 0);
        const netProfit = summary.reduce((a, s) => a + Number(isMtd ? s.net_profit_mtd || 0 : s.net_profit_ytd || 0), 0);
        const cash = summary.reduce((a, s) => a + Number(s.cash_balance || 0), 0);
        const ar = summary.reduce((a, s) => a + Number(s.ar_open || 0), 0);
        const ap = summary.reduce((a, s) => a + Number(s.ap_open || 0), 0);
        const cogsYtd = summary.reduce((a, s) => a + Number(s.cogs_ytd || 0), 0);
        const quick = ap ? (Math.abs(cash) + Math.abs(ar)) / Math.abs(ap) : 0;
        const dso = revenue ? (Math.abs(ar) / Math.abs(summary.reduce((x, s) => x + Number(s.revenue_ytd || 0), 0))) * daysYtd : 0;
        const dpo = cogsYtd ? (Math.abs(ap) / Math.abs(cogsYtd)) * daysYtd : 0;

        return [
            { key: "revenue", label: isMtd ? "Revenue MTD" : "Revenue YTD", type: "money", value: revenue, currencyCode },
            { key: "gross_profit", label: isMtd ? "Contribution Profit MTD" : "Contribution Profit YTD", type: "money", value: grossProfit, currencyCode },
            { key: "net_profit", label: isMtd ? "Net Profit MTD" : "Net Profit YTD", type: "money", value: netProfit, currencyCode },
            { key: "cash", label: "Cash Balance", type: "money", value: cash, currencyCode },
            { key: "ar", label: "AR Open", type: "money", value: ar, currencyCode },
            { key: "ap", label: "AP Open", type: "money", value: ap, currencyCode },
            { key: "dso", label: "DSO (Days Sales Outstanding)", type: "ratio", value: dso },
            { key: "dpo", label: "DPO (Days Payables Outstanding)", type: "ratio", value: dpo },
            { key: "quick_ratio", label: "Quick Ratio", type: "ratio", value: quick },
        ].map((k) => ({ ...k, target: this.getKpiTarget(k) }));
    }

    getKpiTarget(kpi) {
        if (kpi.key === "quick_ratio") {
            if (kpi.value < 1.0) return { level: "bad", label: "Critical" };
            if (kpi.value < 1.2) return { level: "warn", label: "Watch" };
            return { level: "good", label: "Healthy" };
        }
        if (["net_profit", "cash"].includes(kpi.key)) return kpi.value < 0 ? { level: "bad", label: "Negative" } : { level: "good", label: "Positive" };
        return { level: "good", label: "Actual" };
    }

    buildRevenueShareChart(summary, period = "ytd") {
        if (!summary.length) return null;
        const palette = ["#2563eb", "#22c55e", "#f97316", "#7c3aed", "#e11d48", "#06b6d4", "#84cc16", "#f59e0b"];
        const valueKey = period === "mtd" ? "revenue_mtd" : "revenue_ytd";
        const sorted = summary.map((r) => ({ ...r, _value: Math.max(0, Number(r[valueKey] || 0)) })).filter((r) => r._value > 0).sort((a, b) => b._value - a._value);
        const total = sorted.reduce((a, r) => a + r._value, 0);
        if (!total) return null;
        let cumulative = 0;
        const slices = sorted.map((r, idx) => {
            const pct = (r._value / total) * 100;
            const start = cumulative;
            cumulative += pct;
            return { companyId: r.company_id, companyName: r.company_name, currencyCode: r.currency_code || "USD", value: r._value, pct, color: palette[idx % palette.length], start, end: cumulative };
        });
        const gradient = slices.map((s) => `${s.color} ${s.start.toFixed(2)}% ${s.end.toFixed(2)}%`).join(", ");
        return { total, currencyCode: summary[0].currency_code || "USD", donutStyle: `conic-gradient(${gradient})`, slices, periodLabel: period.toUpperCase() };
    }

    buildConsolidatedTrend(monthly) {
        const byMonth = {};
        for (const row of monthly) {
            const key = row.month_start;
            if (!byMonth[key]) byMonth[key] = { month: key, revenue: 0, grossProfit: 0, netProfit: 0, currencyCode: row.currency_code || "USD" };
            byMonth[key].revenue += Number(row.revenue || 0);
            byMonth[key].grossProfit += Number(row.gross_profit || 0);
            byMonth[key].netProfit += Number(row.net_profit || 0);
        }
        return Object.values(byMonth)
            .sort((a, b) => String(a.month).localeCompare(String(b.month)))
            .map((r) => ({ ...r, grossMarginPct: r.revenue ? (r.grossProfit / r.revenue) * 100 : 0, netMarginPct: r.revenue ? (r.netProfit / r.revenue) * 100 : 0 }));
    }

    buildKpiDeltas(trend) {
        if (!trend.length) return {};
        const current = trend[trend.length - 1];
        const prev = trend.length > 1 ? trend[trend.length - 2] : null;
        const py = trend.length > 12 ? trend[trend.length - 13] : null;
        const yoy = this.buildYoYTrendPairs(trend, this.state.selectedPeriod);
        return {
            revenueDeltaPct: prev && prev.revenue ? ((current.revenue - prev.revenue) / Math.abs(prev.revenue)) * 100 : 0,
            netMarginDeltaPct: prev ? current.netMarginPct - prev.netMarginPct : 0,
            revenueYoYPct: py && py.revenue ? ((current.revenue - py.revenue) / Math.abs(py.revenue)) * 100 : 0,
            grossProfitYoYPct: yoy.previous.grossProfit ? ((yoy.current.grossProfit - yoy.previous.grossProfit) / Math.abs(yoy.previous.grossProfit)) * 100 : 0,
            netProfitYoYPct: yoy.previous.netProfit ? ((yoy.current.netProfit - yoy.previous.netProfit) / Math.abs(yoy.previous.netProfit)) * 100 : 0,
            currentMonth: current.month,
            previousMonth: prev ? prev.month : null,
            pyMonth: py ? py.month : null,
        };
    }

    buildYoYTrendPairs(trend, period) {
        const monthly = trend.map((r) => {
            const monthDate = new Date(`${r.month}T00:00:00`);
            return {
                ...r,
                year: monthDate.getFullYear(),
                monthNum: monthDate.getMonth() + 1,
            };
        });
        if (!monthly.length) {
            return {
                current: { revenue: 0, grossProfit: 0, netProfit: 0 },
                previous: { revenue: 0, grossProfit: 0, netProfit: 0 },
            };
        }

        const latest = monthly[monthly.length - 1];
        const currentYear = latest.year;
        const currentMonthNum = latest.monthNum;
        const previousYear = currentYear - 1;

        const isMtd = period === "mtd";
        const currentSet = monthly.filter((r) => r.year === currentYear && (isMtd ? r.monthNum === currentMonthNum : r.monthNum <= currentMonthNum));
        const previousSet = monthly.filter((r) => r.year === previousYear && (isMtd ? r.monthNum === currentMonthNum : r.monthNum <= currentMonthNum));

        const sumSet = (rows) =>
            rows.reduce(
                (acc, r) => ({
                    revenue: acc.revenue + Number(r.revenue || 0),
                    grossProfit: acc.grossProfit + Number(r.grossProfit || 0),
                    netProfit: acc.netProfit + Number(r.netProfit || 0),
                }),
                { revenue: 0, grossProfit: 0, netProfit: 0 }
            );

        return { current: sumSet(currentSet), previous: sumSet(previousSet) };
    }

    buildProfitWaterfall(summary) {
        if (!summary.length) return null;
        const currencyCode = summary[0].currency_code || "USD";
        const isMtd = this.state.selectedPeriod === "mtd";
        const key = isMtd ? "mtd" : "ytd";

        const revenue = summary.reduce((a, s) => a + Math.max(0, Number(s[`revenue_${key}`] || 0)), 0);
        const cogs = Math.abs(summary.reduce((a, s) => a + Number(s[`cogs_${key}`] || 0), 0));
        const opex = Math.abs(summary.reduce((a, s) => a + Number(s[`opex_${key}`] || 0), 0));
        const grossProfit = revenue - cogs;
        const operatingProfit = grossProfit - opex;
        const netProfit = summary.reduce((a, s) => a + Number(s[`net_profit_${key}`] || 0), 0);
        const otherTax = netProfit - operatingProfit;

        const rawSteps = [
            { key: "revenue", label: "Revenue", kind: "anchor", value: revenue },
            { key: "cogs", label: "Direct Cost", kind: "down", value: -cogs },
            { key: "gross", label: "Contribution Profit", kind: "subtotal", value: grossProfit },
            { key: "opex", label: "OpEx", kind: "down", value: -opex },
            { key: "other_tax", label: "Other/Tax", kind: otherTax >= 0 ? "up" : "down", value: otherTax },
            { key: "net", label: "Net Profit", kind: "total", value: netProfit },
        ];

        let running = 0;
        const bounds = [];
        for (const step of rawSteps) {
            if (step.kind === "anchor") {
                running = step.value;
                bounds.push({ min: 0, max: step.value });
                continue;
            }
            if (["subtotal", "total"].includes(step.kind)) {
                running = step.value;
                bounds.push({ min: 0, max: step.value });
                continue;
            }
            const start = running;
            const end = running + step.value;
            bounds.push({ min: Math.min(start, end), max: Math.max(start, end) });
            running = end;
        }
        const globalMin = Math.min(0, ...bounds.map((b) => b.min));
        const globalMax = Math.max(1, ...bounds.map((b) => b.max));
        const span = Math.max(1, globalMax - globalMin);

        const steps = rawSteps.map((step, idx) => {
            const b = bounds[idx];
            return {
                ...step,
                leftPct: ((b.min - globalMin) / span) * 100,
                widthPct: Math.max(1, ((b.max - b.min) / span) * 100),
            };
        });

        return {
            currencyCode,
            periodLabel: key.toUpperCase(),
            steps,
        };
    }

    buildRiskHighlights(aging, summary) {
        const totalAr = summary.reduce((a, s) => a + Math.abs(Number(s.ar_open || 0)), 0);
        const totalAp = summary.reduce((a, s) => a + Math.abs(Number(s.ap_open || 0)), 0);
        const overdue90 = aging.filter((a) => a.partner_type === "receivable" && a.bucket === "90_plus").reduce((a, r) => a + Math.abs(Number(r.amount || 0)), 0);
        const overdue90Pct = totalAr ? (overdue90 / totalAr) * 100 : 0;
        const quickRatio = totalAp ? summary.reduce((a, s) => a + Math.abs(Number(s.cash_balance || 0)) + Math.abs(Number(s.ar_open || 0)), 0) / totalAp : 0;
        return [
            { label: "Overdue AR 90+", value: overdue90, pct: overdue90Pct, type: overdue90Pct >= 25 ? "high" : overdue90Pct >= 15 ? "medium" : "low" },
            { label: "Quick Ratio (Cash+AR / AP)", value: quickRatio, type: quickRatio < 1 ? "high" : quickRatio < 1.2 ? "medium" : "low" },
        ];
    }

    buildAgingBucketTotals(aging) {
        const order = ["not_due", "1_30", "31_60", "61_90", "90_plus"];
        const grouped = {};
        for (const row of aging) grouped[row.bucket] = (grouped[row.bucket] || 0) + Number(row.amount || 0);
        const max = Math.max(...Object.values(grouped), 1);
        return order.map((bucket) => ({ bucket, label: this.formatLabel(bucket), amount: grouped[bucket] || 0, width: Math.max(2, Math.round((Math.abs(grouped[bucket] || 0) / max) * 100)) }));
    }

    buildWhatChanged(summary, monthly, aging) {
        const changes = [];
        const byCompany = {};
        for (const row of monthly) {
            const cid = String(row.company_id);
            if (!byCompany[cid]) byCompany[cid] = [];
            byCompany[cid].push(row);
        }
        const movers = [];
        for (const cid of Object.keys(byCompany)) {
            const rows = byCompany[cid].sort((a, b) => String(a.month_start).localeCompare(String(b.month_start)));
            if (rows.length < 2) continue;
            const curr = rows[rows.length - 1];
            const prev = rows[rows.length - 2];
            const delta = Number(curr.revenue || 0) - Number(prev.revenue || 0);
            const pct = Number(prev.revenue || 0) ? (delta / Math.abs(Number(prev.revenue || 0))) * 100 : 0;
            movers.push({ companyName: curr.company_name, delta, pct });
        }
        movers.sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
        for (const mv of movers.slice(0, 2)) {
            changes.push({ kind: mv.delta >= 0 ? "up" : "down", text: `${mv.companyName} revenue ${mv.delta >= 0 ? "up" : "down"} ${Math.abs(mv.pct).toFixed(1)}% MoM` });
        }
        const overdue90 = aging.filter((a) => a.partner_type === "receivable" && a.bucket === "90_plus").reduce((a, r) => a + Math.abs(Number(r.amount || 0)), 0);
        if (overdue90 > 0) {
            changes.push({ kind: "risk", text: `Overdue AR 90+ at ${this.formatCurrency(overdue90, (summary[0] && summary[0].currency_code) || "USD")}` });
        }
        return changes.slice(0, 3);
    }

    buildProfitabilityRanking(summary) {
        return summary
            .map((s) => {
                const revenueYtd = Number(s.revenue_ytd || 0);
                const netProfitYtd = Number(s.net_profit_ytd || 0);
                return { companyName: s.company_name, currencyCode: s.currency_code || "USD", revenueYtd, netProfitYtd, netMarginPct: revenueYtd ? (netProfitYtd / revenueYtd) * 100 : 0 };
            })
            .sort((a, b) => b.netMarginPct - a.netMarginPct);
    }

    buildDecisionPanel(risks, ranking) {
        const actions = [];
        const arRisk = risks.find((r) => r.label === "Overdue AR 90+");
        const quick = risks.find((r) => r.label.includes("Quick Ratio"));
        const lowMargin = ranking.filter((r) => r.netMarginPct < 10).length;

        if (arRisk && (arRisk.pct || 0) > 15) {
            actions.push({ owner: "CFO", action: "Reduce 90+ AR exposure", impact: `Lower 90+ AR from ${Math.round(arRisk.pct || 0)}% to <15%`, due: "30 days" });
        }
        if (quick && quick.value < 1.2) {
            actions.push({ owner: "Finance Controller", action: "Protect cash and AP coverage", impact: "Keep quick ratio above 1.2", due: "30 days" });
        }
        if (lowMargin > 0) {
            actions.push({ owner: "CEO + Ops", action: "Lift low-margin companies", impact: `${lowMargin} companies below 10% net margin`, due: "60 days" });
        }
        if (!actions.length) {
            actions.push({ owner: "Board", action: "No actions required", impact: "All tracked indicators are within target thresholds.", due: "Monitor" });
        }
        return actions;
    }

    buildAuditability(summary, monthly, aging) {
        const summaryRevenueYtd = summary.reduce((acc, s) => acc + Number(s.revenue_ytd || 0), 0);
        const monthlyRevenueYtd = monthly.reduce((acc, m) => acc + Number(m.revenue || 0), 0);
        const revenueGap = summaryRevenueYtd - monthlyRevenueYtd;

        const summaryAr = summary.reduce((acc, s) => acc + Math.abs(Number(s.ar_open || 0)), 0);
        const agingAr = aging.filter((a) => a.partner_type === "receivable").reduce((acc, a) => acc + Math.abs(Number(a.amount || 0)), 0);
        const arGap = summaryAr - agingAr;

        return {
            snapshotDate: this.state.snapshotDate || "-",
            refreshedAt: this.state.refreshedAt,
            period: this.state.selectedPeriod.toUpperCase(),
            checks: [
                { label: "Revenue Consistency (Summary vs Monthly)", gap: revenueGap, status: Math.abs(revenueGap) < 0.01 ? "ok" : "warn" },
                { label: "AR Consistency (Summary vs Aging)", gap: arGap, status: Math.abs(arGap) < 0.01 ? "ok" : "warn" },
            ],
        };
    }

    buildBenchmarking(summary, monthly, aging) {
        if (!summary.length) return [];
        const byCompany = {};
        for (const row of monthly) {
            const cid = String(row.company_id);
            if (!byCompany[cid]) byCompany[cid] = [];
            byCompany[cid].push(row);
        }
        const growthByCompany = {};
        for (const cid of Object.keys(byCompany)) {
            const rows = byCompany[cid].sort((a, b) => String(a.month_start).localeCompare(String(b.month_start)));
            if (rows.length < 2) {
                growthByCompany[cid] = 0;
                continue;
            }
            const curr = Number(rows[rows.length - 1].revenue || 0);
            const prev = Number(rows[rows.length - 2].revenue || 0);
            growthByCompany[cid] = prev ? ((curr - prev) / Math.abs(prev)) * 100 : 0;
        }

        const ar90ByCompany = {};
        for (const row of aging) {
            if (row.partner_type !== "receivable" || row.bucket !== "90_plus") continue;
            const cid = String(row.company_id);
            ar90ByCompany[cid] = (ar90ByCompany[cid] || 0) + Math.abs(Number(row.amount || 0));
        }

        const rows = summary.map((s) => {
            const cid = String(s.company_id);
            const revenueYtd = Number(s.revenue_ytd || 0);
            const netProfitYtd = Number(s.net_profit_ytd || 0);
            const arOpen = Math.abs(Number(s.ar_open || 0));
            const ar90 = ar90ByCompany[cid] || 0;
            return {
                companyId: s.company_id,
                companyName: s.company_name,
                growthPct: growthByCompany[cid] || 0,
                netMarginPct: revenueYtd ? (netProfitYtd / revenueYtd) * 100 : 0,
                ar90Pct: arOpen ? (ar90 / arOpen) * 100 : 0,
            };
        });

        const median = (arr) => {
            const x = [...arr].sort((a, b) => a - b);
            if (!x.length) return 0;
            const m = Math.floor(x.length / 2);
            return x.length % 2 ? x[m] : (x[m - 1] + x[m]) / 2;
        };
        const mg = median(rows.map((r) => r.growthPct));
        const mm = median(rows.map((r) => r.netMarginPct));
        const ma = median(rows.map((r) => r.ar90Pct));

        return rows
            .map((r) => ({
                ...r,
                growthVsMedian: r.growthPct - mg,
                marginVsMedian: r.netMarginPct - mm,
                ar90VsMedian: r.ar90Pct - ma,
            }))
            .sort((a, b) => b.netMarginPct - a.netMarginPct);
    }

    buildCashRunway(summary, cashMonthly) {
        if (!summary.length) return null;
        const currencyCode = summary[0].currency_code || "USD";
        const totalCash = summary.reduce((a, s) => a + Number(s.cash_balance || 0), 0);
        const totalOpexYtd = summary.reduce((a, s) => a + Number(s.opex_ytd || 0), 0);
        const monthsElapsed = new Date().getMonth() + 1;
        const avgMonthlyOpex = monthsElapsed ? Math.abs(totalOpexYtd) / monthsElapsed : 0;
        const runwayMonths = avgMonthlyOpex ? Math.abs(totalCash) / avgMonthlyOpex : 0;

        const byMonth = {};
        for (const row of cashMonthly) {
            const month = row.month_start;
            byMonth[month] = (byMonth[month] || 0) + Number(row.cash_balance || 0);
        }
        const series = Object.keys(byMonth)
            .sort((a, b) => String(a).localeCompare(String(b)))
            .slice(-6)
            .map((m) => ({ month: m, cash: byMonth[m] }));

        return {
            currencyCode,
            cash: totalCash,
            avgMonthlyOpex,
            runwayMonths,
            status: runwayMonths < 3 ? "critical" : runwayMonths < 6 ? "watch" : "healthy",
            series,
        };
    }

    buildMultiCurrencyWarning(summary) {
        const currencies = [...new Set(summary.map((s) => s.currency_code).filter(Boolean))];
        if (currencies.length <= 1) return null;
        return `Mixed currencies detected (${currencies.join(", ")}). Consolidated totals are not FX-converted.`;
    }

    exportSnapshotPdf() {
        this.action.doAction("account_board_dashboard.action_report_board_dashboard_pdf", {
            additionalContext: { board_period: this.state.selectedPeriod || "ytd" },
        });
    }

    onKpiTileClick(kpi) {
        if (!kpi || !kpi.key) return;
        if (kpi.key === "ar") {
                this.openDrill(
                    [
                        ["move_id.state", "=", "posted"],
                        ["account_id.account_type", "=", "asset_receivable"],
                        ["amount_residual", "!=", 0],
                    ],
                    "Open Receivables Entries",
                    [[false, "pivot"], [false, "list"], [false, "graph"]],
                    {
                        search_default_group_by_partner_id: 1,
                        search_default_group_by_date_maturity: 1,
                        pivot_measures: ["amount_residual"],
                    }
                );
        }
        if (kpi.key === "ap") {
            this.openDrill(
                [
                    ["move_id.state", "=", "posted"],
                        ["account_id.account_type", "=", "liability_payable"],
                        ["amount_residual", "!=", 0],
                    ],
                    "Open Payables Entries",
                    [[false, "pivot"], [false, "list"], [false, "graph"]],
                    {
                        search_default_group_by_partner_id: 1,
                        search_default_group_by_date_maturity: 1,
                        pivot_measures: ["amount_residual"],
                    }
                );
        }
    }

    openDrill(domain, name = "Details", views = [[false, "list"], [false, "form"]], context = {}) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name,
            res_model: "account.move.line",
            views,
            target: "current",
            domain,
            context,
        });
    }

    onDrillRevenueShare(companyId) {
        this.openDrill(
            [
                ["company_id", "=", companyId],
                ["move_id.state", "=", "posted"],
                ["account_id.account_type", "in", ["income", "income_other"]],
            ],
            "Revenue by Customer/Product",
            [[false, "pivot"], [false, "graph"], [false, "list"]],
            { search_default_group_by_partner_id: 1, search_default_group_by_product_id: 1 }
        );
    }

    onDrillOverdueAr() {
        this.openDrill(
            [
                ["move_id.state", "=", "posted"],
                ["account_id.account_type", "=", "asset_receivable"],
                ["amount_residual", "!=", 0],
                ["date_maturity", "<", new Date().toISOString().slice(0, 10)],
            ],
            "Overdue Receivables",
            [[false, "pivot"], [false, "list"], [false, "graph"]],
            { search_default_group_by_partner_id: 1, search_default_group_by_date_maturity: 1 }
        );
    }
}

registry.category("actions").add("account_board_dashboard.action_dashboard", AccountBoardDashboardAction);
