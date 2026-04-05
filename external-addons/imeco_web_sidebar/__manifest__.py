{
    'name': 'IMECO - Web Sidebar', 
    'summary': 'Adds a sidebar to the main screen',
    'description': '''
        This module adds a sidebar to the main screen. The sidebar has a list
        of all installed apps similar to the home menu to ease navigation.
    ''',
    'version': '19.0.1.1.9',
    'category': 'Tools/UI',
    'license': 'LGPL-3', 
    'author': 'IMECO',
    'website': 'http://www.imannuelvictor.com',
    # 'live_test_url': 'https://youtu.be/kmu69REqKDU',
    'contributors': [
        'Victor Imannuel <hi@imannuelvictor.com>',
    ],
    'depends': [
        'base_setup',
        'web',
    ],
    'data': [
        'templates/webclient.xml',
        'views/res_users.xml',
        'views/res_config_settings.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            'imeco_web_sidebar/static/src/scss/variables.scss',
            'imeco_web_sidebar/static/src/scss/colors.scss',
        ],
        'web._assets_backend_helpers': [
            'imeco_web_sidebar/static/src/scss/mixins.scss',
        ],
        'web.assets_web_dark': [
            (
                'after',
                'imeco_web_sidebar/static/src/scss/variables.scss',
                'imeco_web_sidebar/static/src/scss/variables.dark.scss',
            ),
        ],
        'web.assets_backend': [
            (
                'after',
                'web/static/src/webclient/webclient.js',
                'imeco_web_sidebar/static/src/webclient/webclient.js',
            ),
            (
                'after',
                'web/static/src/webclient/webclient.xml',
                'imeco_web_sidebar/static/src/webclient/webclient.xml',
            ),
            (
                'after',
                'web/static/src/webclient/webclient.js',
                'imeco_web_sidebar/static/src/webclient/menus/app_menu_service.js',
            ),
            (
                'after',
                'web/static/src/webclient/webclient.js',
                'imeco_web_sidebar/static/src/webclient/sidebar/sidebar.js',
            ),
            'imeco_web_sidebar/static/src/webclient/webclient.scss',
            'imeco_web_sidebar/static/src/webclient/navbar.xml',
            'imeco_web_sidebar/static/src/webclient/sidebar/sidebar.xml',
            'imeco_web_sidebar/static/src/webclient/sidebar/sidebar.scss',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': '_setup_module',
}
