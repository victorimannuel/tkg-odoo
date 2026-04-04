{
    'name': 'Referrer Credit System',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Manage referrer credits and commissions for sales orders',
    'description': """
Referrer Credit System
======================
This module allows selecting a "Referrer Partner" on Sales Orders.
Referrers earn credits when the customer invoice is paid.
Credits are tracked in a ledger and can be used for future purchases.

Key Features:
- Select Referrer on Sales Order.
- Configurable Commission Percentage.
- Ledger-based credit tracking (Earn/Redeem).
- Credits granted only on paid invoices.
- Partner credit balance and history.
    """,
    'author': 'Custom',
    'depends': ['sale_management', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/product_data.xml',
        'wizard/apply_referrer_credit_views.xml',
        'views/referrer_credit_ledger_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_items.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
