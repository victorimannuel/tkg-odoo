{
    "name": "POS Cart Sale Order",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Create draft Sale Orders directly from POS cart for later settlement.",
    "depends": ["point_of_sale", "sale_management", "pos_sale"],
    "data": [],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_cart_sale_order/static/src/pos/create_sale_order_button.js",
            "pos_cart_sale_order/static/src/pos/create_sale_order_button.xml",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}

