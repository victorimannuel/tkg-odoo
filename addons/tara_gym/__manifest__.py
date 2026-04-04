{
    'name': 'TARA Gym Management',
    'version': '19.0.1.0.0',
    'category': 'Services/Gym',
    'summary': 'Complete Gym & Fitness Club Management System',
    'description': """
        Gym / Fitness Club Management System
        ====================================
        
        Features:
        - Member Management
        - Membership & Subscription (Pro-rated billing)
        - Billing & Payments (Invoicing)
        - Check-in / Attendance (QR/RFID ready)
        - Trainer Management
        - Class / Session Management
        - Room / Facility Management
        - Member Portal
        
        Designed for Odoo 19.
    """,
    'author': 'Victor',
    'depends': ['base', 'account', 'mail', 'portal', 'web', 'point_of_sale', 'stock'],
    'data': [
        # Security
        'security/gym_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/ir_sequence_data.xml',
        'data/gym_data.xml',
        'data/gym_cron.xml',

        # Views - People
        'views/gym_member_views.xml',
        'views/gym_member_tag_views.xml',
        'views/gym_visitor_views.xml',
        'views/gym_trainer_views.xml',

        # Views - Memberships
        'views/gym_membership_views.xml',
        'views/gym_membership_subscription_views.xml',
        'views/gym_membership_benefit_usage_views.xml',

        # Views - Classes
        'views/gym_class_views.xml',
        'views/gym_class_session_views.xml',
        'views/gym_class_enrollment_views.xml',
        'views/gym_schedule_views.xml',

        # Views - Facilities
        'views/gym_door_views.xml',
        'views/gym_room_views.xml',

        # Views - Services
        'views/gym_service_views.xml',
        'views/gym_service_booking_views.xml',
        'views/product_category_views.xml',
        'views/res_config_settings_views.xml',
        
        # Views - Portals
        'views/gym_portal_templates.xml',

        # Views - Menu
        'wizard/gym_checkin_wizard_views.xml',
        'wizard/gym_class_enrollment_create_wizard_views.xml',
        'wizard/gym_schedule_create_wizard_views.xml',
        'wizard/gym_drop_in_wizard_views.xml',
        'views/menus.xml',

        # Reports
        'reports/gym_member_reports.xml',
    ],
    'demo': [
        'demo/gym_demo.xml',
    ],
    'images': [
        'static/description/icon.png',
    ],
    'assets': {
        'web.assets_backend': [
            'tara_gym/static/src/scss/gym_schedule_day_renderer.scss',
            'tara_gym/static/src/js/gym_schedule_calendar.js',
            'tara_gym/static/src/js/gym_schedule_day_renderer.js',
            'tara_gym/static/src/xml/gym_schedule_day_renderer.xml',
            'tara_gym/static/src/js/camera_image_field.js',
            'tara_gym/static/src/xml/camera_image_field.xml',

            # DEPRECATED
            # 'tara_gym/static/src/js/auto_redirect.js',
            # 'tara_gym/static/src/js/booking_type_context.js',
        ],
        'point_of_sale._assets_pos': [
            'tara_gym/static/src/pos/navbar_patch.js',
            'tara_gym/static/src/pos/navbar_patch.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
