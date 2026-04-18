{
    'name': 'Project Notification Sound',
    'version': '1.0',
    'summary': 'Play notification sounds for Project Task assignments',
    'category': 'Services/Project',
    'depends': ['mail', 'project'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'project_notification_sound/static/src/services/out_of_focus_service_patch.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
