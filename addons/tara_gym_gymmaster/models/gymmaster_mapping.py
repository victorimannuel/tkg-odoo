GYMMASTER_ENDPOINTS = {
    "members": {
        "path": "/portal/api/v1/members",
        "model": "gym.member",
        "external_id_field": "gymmaster_member_id",
        "key": "id",
        "fields": {
            "firstname": "firstname",
            "surname": "surname",
            "email": "email",
            "phone": "phone",
            "dob": "date_of_birth",
            "addressstreet": "street",
            # "addresssuburb": "state",
            "addresscity": "city",
            "addresscountry": "country",
            "addressareacode": "zip",
            "joindate": "join_date",
        },
    },
    "memberships": {
        "path": "/portal/api/v1/memberships",
        "model": "gym.membership",
        "external_id_field": "gymmaster_membership_id",
        "key": "id",
        "fields": {
            "name": "name",
            "membership_length": "duration",
            "price": "price",
        },
    },
    "products": {
        "path": "/portal/api/v2/products",
        "model": "product.product",
        "external_id_field": "gymmaster_product_id",
        "key": "productid",
        "fields": {
            "name": "name",
            "description": "description_sale",
            "price": "list_price",
        },
    },
}
