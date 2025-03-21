from django.test import TestCase

# Create your tests here.

from django_tasks import task
from .models import Invoice, InvoiceItem, InvoiceTemplate

@task
def notify_invoice_update(invoice_id):
    invoice = Invoice.objects.get(pk=invoice_id)

    invoice.send_notification()