{
    'name': 'Gestion de Tickets',
    'version': '1.0',
    'summary': 'Module de gestion des tickets',
    'description': 'Module permettant de créer et gérer des tickets',
    'author': 'Ogoouée Technologie',
    'category': 'Technique',
    'website': 'https://new.ogoouetech.com',
    'sequence': -100,
    'depends': ['base', 'web', 'bus'],
    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/ticket_graph.xml',
        'views/ticket_create.xml',
        'views/ticket_list.xml',
        'views/dashboard_action.xml',
        'views/config_ticket.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            # Chargement des bibliothèques tierces en premier
            'https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js',
            'https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js',

            # Scripts et styles de votre module
            '/ticket/static/src/css/ticket.css',
            'ticket/static/src/js/dashboard.js',
            'ticket/static/src/xml/dashboard.xml', 
            'ticket/static/src/css/dashboard.css',
            'ticket/static/src/css/styleswitcher.css',
            'ticket/static/src/css/header.css',
        ],
    }
}
