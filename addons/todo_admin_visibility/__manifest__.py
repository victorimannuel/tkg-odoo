# -*- coding: utf-8 -*-
{
    'name': 'Todo Admin Visibility',
    'version': '19.0.1.0.0',
    'summary': 'Allow administrators to read all todo items',
    'category': 'Productivity',
    'author': 'TKG',
    'license': 'LGPL-3',
    'depends': ['base', 'todo'],
    'data': [
        'security/todo_security.xml',
    ],
    'installable': True,
    'application': False,
}
