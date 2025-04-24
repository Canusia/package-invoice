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
        {
            'name': 'pending_invoices',
            'title': 'Pending High Schools Invoices Export',
            'app': 'invoice',
            'description': 'Select the class section terms and registration status to generate a list of high schools that have registrations in those term(s) but no invoice for the selected invoice term with the given prefix.',
            'categories': [
                'Misc.'
            ],
            'available_for': [
                'ce'
            ]
        }
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
        {
            'name': 'pending_invoices',
            'title': 'Pending High Schools Invoices Export',
            'app': 'invoice.invoice',
            'description': 'Select the class section terms and registration status to generate a list of high schools that have registrations in those term(s) but no invoice for the selected invoice term with the given prefix.',
            'categories': [
                'Misc.'
            ],
            'available_for': [
                'ce'
            ]
        }
    ]

    def ready(self):
        import invoice.invoice.signals
        