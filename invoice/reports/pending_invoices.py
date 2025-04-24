import logging, datetime
from operator import or_
from functools import reduce
import os, io
import zipfile
from io import BytesIO

from django import forms
from django.db.models import Q

from django.urls import reverse_lazy
from django.forms import ValidationError

import csv
from django.http import HttpResponse

from django.utils import timezone
from cis.utils import get_field

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.core.files.base import ContentFile, File

from ..models import Invoice

from cis.utils import export_to_excel
from cis.models.term import Term


from django.http import HttpResponse

from cis.utils import get_field

from cis.backends.storage_backend import PrivateMediaStorage
from cis.models.section import StudentRegistration
from cis.models.highschool import HighSchool

logger = logging.getLogger(__name__)

class pending_invoices(forms.Form):

    class_section_terms = forms.ModelMultipleChoiceField(
        queryset=None,
        required=True,
        label='Class Section Term(s)'
    )

    registration_status = forms.MultipleChoiceField(
        choices=StudentRegistration.STATUS_OPTIONS,
        required=True,
        widget=forms.CheckboxSelectMultiple,
        label='Registration Status to Include',
        help_text='Select all that apply'
    )

    term = forms.ModelChoiceField(
        queryset=None,
        required=True,
        label='Invoice Term'
    )

    invoice_prefix = forms.CharField(
        label='Invoice Prefix',
        required=True,
        help_text='Enter the invoice prefix to filter by'
    )

    roles = []
    request = None
    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.request = request

        self.helper = FormHelper()
        self.helper.attrs = {'target':'_blank'}
        self.helper.form_method = 'POST'

        if self.request:
            self.roles = request.user.get_roles()
            self.helper.form_action = reverse_lazy(
                'report:run_report', args=[request.GET.get('report_id')]
            )
            
        self.helper.add_input(Submit('submit', 'Generate Export'))
        self.fields['term'].queryset = Term.objects.all().order_by('-code')
        self.fields['class_section_terms'].queryset = Term.objects.all().order_by('-code')

    def run(self, task, data):
        
        # get highschools that have registrations in the selected class terms and where students are in the statuss selected
        highschools = StudentRegistration.objects.filter(
            class_section__term__in=data.get('class_section_terms'),
            status__in=data.get('registration_status')
        ).values_list('student__highschool__id', flat=True)

        # get all invoices for the selected term and prefix
        invoice_highschools = Invoice.objects.filter(
            term__in=data.get('term'),
            number__startswith=data.get('invoice_prefix')[0]
        ).values_list('highschool__id', flat=True)

        records = HighSchool.objects.filter(
            id__in=highschools
        ).exclude(
            id__in=invoice_highschools
        )

        file_name = "pending_highschool_invoices_export.csv"
        fields = {
            'class_section.class_number': 'High School',
            'class_section.class_number': 'District'
        }
        
        import csv
        stream = io.StringIO()
        writer = csv.writer(stream, delimiter=',')

        writer.writerow(fields.values())
        for record in records:
            row = []
            
            row.append(record.name)
            if record.highschool.district:
                row.append(record.highschool.district.name)
            else:
                row.append('')
                
            writer.writerow(row)
        
        path = "reports/" + str(task.id) + "/" + file_name
        media_storage = PrivateMediaStorage()

        path = media_storage.save(path, ContentFile(stream.getvalue().encode('utf-8')))
        path = media_storage.url(path)

        return path
        
