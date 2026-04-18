{
    'name': 'IMECO POS Order Cancel',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Backend POS order cancellation with required reason.',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
