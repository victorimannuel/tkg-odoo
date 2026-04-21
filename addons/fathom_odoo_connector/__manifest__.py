{
    'name': 'Fathom Odoo Connector',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'summary': 'API-first connector between Odoo and Fathom',
    'author': 'Victor',
    'depends': ['base', 'base_setup', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/res_config_settings_views.xml',
        'views/fathom_sync_log_views.xml',
        'views/fathom_external_map_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
