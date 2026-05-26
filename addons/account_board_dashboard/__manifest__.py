{
    "name": "Accounting Board Dashboard",
    "version": "19.0.1.0.0",
    "summary": "Board-level accounting KPI dashboard",
    "category": "Accounting/Accounting",
    "author": "TKG",
    "license": "LGPL-3",
    "depends": ["account", "spreadsheet_dashboard"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/account_board_dashboard_views.xml",
        "report/report_board_dashboard_pdf.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_board_dashboard/static/src/js/account_board_dashboard_action.js",
            "account_board_dashboard/static/src/xml/account_board_dashboard_templates.xml",
            "account_board_dashboard/static/src/scss/account_board_dashboard.scss",
        ],
    },
    "installable": True,
    "application": False,
}
