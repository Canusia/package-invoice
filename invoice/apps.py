from django.apps import AppConfig

class InvoiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'invoice'

    CONFIGURATORS = [
        {
            'app': 'invoice',
            'name': 'invoice',
            'title': 'Invoice Settings',
            'description': '-',
            'categories': [
                '4'
            ]
        },
    ]

    REPORTS = [
        {
            'name': 'invoices',
            'title': 'Invoices Export',
            'app': 'invoice',
            'description': '-',
            'categories': [
                'Misc.'
            ],
            'available_for': [
                'ce'
            ]
        },
    ]


    def ready(self):
        import invoice.signals

class DevInvoiceConfig(AppConfig):
    name = 'invoice.invoice'

    CONFIGURATORS = [
        {
            'app': 'invoice.invoice',
            'name': 'invoice',
            'title': 'Invoice Settings',
            'description': '-',
            'categories': [
                '4'
            ]
        },
    ]
    
    REPORTS = [
        {
            'name': 'invoices',
            'title': 'Invoices Export',
            'app': 'invoice.invoice',
            'description': '-',
            'categories': [
                'Misc.'
            ],
            'available_for': [
                'ce'
            ]
        },
    ]

    def ready(self):
        import invoice.invoice.signals
        