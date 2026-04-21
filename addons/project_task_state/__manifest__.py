{
    'name': 'Project Task Custom State',
    'version': '1.0',
    'summary': 'Add Pending state to project tasks',
    'category': 'Services/Project',
    'depends': ['project'],
    'data': [
        'data/mail_message_subtype_data.xml',
        'views/project_task_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'project_task_state/static/src/components/project_task_state_selection/project_task_state_selection.js',
            'project_task_state/static/src/css/task_state_colors.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
