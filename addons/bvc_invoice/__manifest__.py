{
    'name': 'BVC - Invoice Customization',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Custom Invoice Report Layout for BVC',
    'description': """
        Customizes the standard customer invoice report:
        - Replaces the standard document template with a custom implementation
        - Modifies the header layout
    """,
    'author': 'hi@imannuelvictor.com',
    'depends': ['account'],
    
    'assets': {
        'web.assets_backend': [
            '/bvc_invoice/static/src/css/fonts.css',
        ],
        'web.report_assets_common': [
            '/bvc_invoice/static/src/css/fonts.css',
        ],
    },

    'data': [
        'reports/report_invoice.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
