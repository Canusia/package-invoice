from django.conf import settings

from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.contrib.sites.models import Site

from django.template import Context, Template
from django.template.loader import get_template, render_to_string

from .models import InvoiceItem, Invoice

from .settings.invoice import invoice as InvoiceSettings

@receiver(post_save, sender=InvoiceItem)
def line_item_updated(sender, instance, created, **kwargs):
    
    invoice = instance.invoice

    invoice.update_total()

@receiver(post_delete, sender=InvoiceItem)
def line_item_deleted(sender, instance, **kwargs):
    
    invoice = instance.invoice
    invoice.update_total()


@receiver(post_save, sender=Invoice)
def invoice_updated(sender, instance, created, **kwargs):
    
    configs = InvoiceSettings.from_db()

    if configs.get('is_active', 'No') == 'No':
        return
    
    if instance.status in configs.get('status_notification_trigger', []):
        instance.send_notification()
