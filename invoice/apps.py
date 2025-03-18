from django.apps import AppConfig

class InvoiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'invoice'

    CONFIGURATORS = []
    REPORTS = []

class DevInvoiceConfig(AppConfig):
    name = 'invoice.invoice'

    CONFIGURATORS = InvoiceConfig.CONFIGURATORS
    REPORTS = InvoiceConfig.REPORTS
