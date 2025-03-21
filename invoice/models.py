import uuid, datetime, csv
from django.http import HttpResponse
from io import BytesIO

import pdfkit
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.db import models
from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models import JSONField, Sum
from django.core.mail import EmailMessage, send_mail
from django.template.loader import render_to_string
from django.urls import reverse_lazy

from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template import Context, Template
from django.template.loader import get_template, render_to_string

from mailer import send_mail, send_html_mail

from cis.settings.pd_event import pd_event
from cis.utils import export_to_excel, event_file_upload_path, getDomain
from cis.storage_backend import PrivateMediaStorage
from cis.models.note import Note
from cis.models.customuser import CustomUser

from .settings.invoice import invoice as InvoiceSettings

class InvoiceTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)

    description = models.TextField(
        blank=True,
        null=True
    )

    def __str__(self):
        return self.name
    
    @property
    def ce_url(self):
        return reverse_lazy('invoice:invoice_template', kwargs={
            'record_id': self.id
        })
    
class Invoice(models.Model):
    """
    Invoice model
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.CharField(max_length=100)

    created_on = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('cis.CustomUser', on_delete=models.PROTECT)

    highschool = models.ForeignKey('cis.HighSchool', on_delete=models.PROTECT, blank=True, null=True)

    term = models.ForeignKey('cis.Term', on_delete=models.PROTECT)
    
    template = models.ForeignKey('invoice.InvoiceTemplate', on_delete=models.PROTECT, blank=True, null=True)

    due_date = models.DateField(
        verbose_name="Due Date",
        blank=True,
        null=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    meta = JSONField(
        default=dict,
        blank=True,
        null=True
    )

    STATUS_OPTIONS = [
        ('', 'Select'),
        ('Draft', 'Draft'),
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Cancelled', 'Cancelled'),
    ]
    status = models.CharField(
        max_length=10,
        verbose_name='Status',
        choices=STATUS_OPTIONS,
        blank=True,
        null=True,
        default='Draft'
    )

    total_amount = models.FloatField(
        default=0.0,
        verbose_name='Total Amount',
        null=True,
    )

    def __str__(self):
        return self.number
    
    class Meta:
        ordering = ['number']

    @property
    def tracking_url(self):
        from cis.utils import getDomain
        url = getDomain() + reverse_lazy('invoice:track_email') + f"?invoice={self.id}&date=" + datetime.datetime.now().strftime('%Y-%m-%d')

        return url
    
    @property
    def ce_url(self):
        return reverse_lazy('invoice:invoice', kwargs={
            'record_id': self.id
        })
    
    def send_notification(self):
        configs = InvoiceSettings.from_db()
        record = self

        subject = configs.get(f"status_change_{record.status}_subject", 'Change me')
        message = Template(configs.get(f"status_change_{record.status}_email", 'Change me'))

        context = {
            'invoice_due_date': record.due_date.strftime('%m/%d/%Y'),
            'invoice_amount': record.formatted_amount,
            'invoice_number': record.number,
            'invoice_term': record.term.label,
            'invoice_status': record.status,
            'billing_contact': record.billing_contact,
            'school_name': record.highschool.name,
            'school_address': record.school_address,
            'invoice_description': record.description,
            'line_items': record.line_items_sexy,
            'invoice': record
        }

        message = message.render(Context(context))
        message += record.tracking_url

        to = [
            record.billing_contact_email
        ]

        if configs.get('is_active') == 'Debug':
            to = configs.get('debug_list', 'kadaji@gmail.com').split(',')

        # Create email
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to
        )
        
        email.content_subtype = "html"

        file_attached = False
        if configs.get(f"status_change_{record.status}_attach_invoice", False):
            pdf = record.as_pdf()

            # Convert to BytesIO
            pdf_file = BytesIO(pdf)

            # Attach PDF file
            email.attach(f'invoice-{record.number}.pdf', pdf_file.getvalue(), 'application/pdf')
            
            file_attached = True

        # Send email
        email.send(fail_silently=True)

        record.add_note(None, f'Sent email to {to}<br>{message}<br>File Attached - {file_attached}')

    def as_pdf(self, mode='pdf'):
        record = self

        options = {
            'page-size': 'Letter'
        }

        base_template = 'invoice/base.html'
        template = get_template(base_template)

        invoice_template = Template(record.template.description)
        context = {
            'invoice_due_date': record.due_date.strftime('%m/%d/%Y'),
            'invoice_amount': record.formatted_amount,
            'invoice_number': record.number,
            'invoice_term': record.term.label,
            'invoice_status': record.status,
            'billing_contact': record.billing_contact,
            'school_name': record.highschool.name,
            'school_address': record.school_address,
            'invoice_description': record.description,
            'line_items': record.line_items_sexy,
            'invoice': record
        }
        main_html = invoice_template.render(Context(context))

        html = template.render({'main_html': main_html})

        if mode == 'html':
            return html
        
        pdf = pdfkit.from_string(html, False, options)
        return pdf

    @property
    def billing_contact(self):
        from cis.models.highschool_administrator import HSAdministratorPosition
        primary_contact = HSAdministratorPosition.objects.filter(
            position__id=self.meta.get('billing_contact_id')
        )

        if primary_contact:
            return f"{primary_contact[0].hsadmin.user.first_name} {primary_contact[0].hsadmin.user.last_name}"
        else:
            primary_contact = HSAdministratorPosition.objects.filter(
                position__id=self.meta.get('alt_billing_contact_id')
            )

        if primary_contact:
            return f"{primary_contact[0].hsadmin.user.first_name} {primary_contact[0].hsadmin.user.last_name}"
        
        return 'N/A'
    
    @property
    def billing_contact_email(self):
        from cis.models.highschool_administrator import HSAdministratorPosition
        primary_contact = HSAdministratorPosition.objects.filter(
            position__id=self.meta.get('billing_contact_id')
        )

        if primary_contact:
            return primary_contact[0].hsadmin.user.email
        else:
            primary_contact = HSAdministratorPosition.objects.filter(
                position__id=self.meta.get('alt_billing_contact_id')
            )

        if primary_contact:
            return primary_contact[0].hsadmin.user.email
        
        return 'N/A'

    @property
    def line_items_sexy(self):
        line_items = self.invoiceitem_set.all()

        result = ""
        for item in line_items:
            result += f"<tr><td>{item.description}</td><td>{item.formatted_amount}</td></tr>"
        
        return mark_safe(result)
    
    @property
    def school_address(self):
        return mark_safe(
            f"{self.highschool.address1}<br>{self.highschool.city} {self.highschool.state} - {self.highschool.postal_code}"
        )
    
    @property
    def formatted_amount(self):
        return f"${self.total_amount:.2f}"
    
    def update_total(self):
        total = self.invoiceitem_set.all().aggregate(total=Sum('amount'))
        self.total_amount = total.get('total')
        self.save()
        
    def add_note(self, createdby=None, note='', meta=None):

        if not createdby:
            createdby = CustomUser.objects.get(
                username='cron'
            )

        note = InvoiceNote(
            createdby=createdby,
            note=note,
            invoice=self
        )

        if not meta:
            meta = {'type': 'private'}

        note.meta = meta
        note.save()

        return note
    
    def clone(self):
        # Clone the invoice
        cloned_invoice = Invoice.objects.create(
            number=f"{self.number}-clone",
            created_by=self.created_by,
            highschool=self.highschool,
            term=self.term,
            template=self.template,
            due_date=self.due_date,
            description=self.description,
            meta=self.meta,
            status=self.status,
            total_amount=self.total_amount,
        )

        # Clone related invoice items
        for item in self.invoiceitem_set.all():
            InvoiceItem.objects.create(
                created_by=item.created_by,
                invoice=cloned_invoice,
                description=item.description,
                meta=item.meta,
                amount=item.amount,
            )

        return cloned_invoice

class InvoiceNote(Note, models.Model):
    invoice = models.ForeignKey(
        'invoice.Invoice',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )

    meta = JSONField(blank=True, null=True)
    class Meta:
        ordering = ['createdon']

    @property
    def sexy_note(self):
        return mark_safe(self.note)

class InvoiceItem(models.Model):
    """
    Invoice model
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
            
    created_on = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('cis.CustomUser', on_delete=models.PROTECT)
    
    invoice = models.ForeignKey('invoice.Invoice', on_delete=models.PROTECT, blank=True, null=True)

    description = models.TextField(
        blank=True,
        null=True
    )

    meta = JSONField(
        default=dict,
        blank=True,
        null=True
    )

    amount = models.FloatField(
        default=0.0,
        verbose_name='Amount',
        null=True,
    )
    
    @property
    def formatted_amount(self):
        return f"${self.amount:.2f}"