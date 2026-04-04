{
    'name': 'POS Screen Layout',
    'version': '19.0.2.0.0',
    'category': 'Point of Sale',
    'summary': 'Swap left/right panes on the POS screen',
    'description': 'Configurable option to swap the left and right panes on the POS product and payment screens.',
    'depends': ['point_of_sale'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_screen_layout/static/src/product_screen_patch.xml',
            'pos_screen_layout/static/src/payment_screen_patch.xml',
            'pos_screen_layout/static/src/product_screen_patch.scss',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    # 'pre_init_hook': 'pre_init_hook',
}
