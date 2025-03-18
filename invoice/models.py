import uuid
import csv
from django.http import HttpResponse

from django.utils import timezone
from django.db import models
from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models import JSONField
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

    def __str__(self):
        return self.number
    
    class Meta:
        ordering = ['number']

class InvoiceItem(models.Model):
    """
    Invoice model
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
            
    created_on = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('cis.CustomUser', on_delete=models.PROTECT)

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
    
