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

logger = logging.getLogger(__name__)

class invoices(forms.Form):

    term = forms.ModelMultipleChoiceField(
        queryset=None,
        label='Term(s)',
        required=True
    )

    invoice_prefix = forms.CharField(
        label='Invoice Prefix',
        required=False
    )

    export_invoices = forms.BooleanField(
        required=False
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

    def run(self, task, data):
        
        media_storage = PrivateMediaStorage()
        records = Invoice.objects.filter(
            term__id__in=data.get('term')
        )

        if data.get('invoice_prefix')[0]:
            records = records.filter(
                number__startswith=data.get('invoice_prefix')[0]
            )
    
        stream = io.StringIO()
        writer = csv.writer(stream, delimiter=',')
        
        ZIPFILE_NAME = f"invoices_export_" + datetime.datetime.now().strftime('%Y_%m_%d') + ".zip"
        b =  BytesIO()

        path_prefix = f'reports/' + datetime.datetime.now().strftime('%Y/%m') + f'/{task.id}/'
    
        # Write Header
        writer.writerow([
            'Term',
            'Invoice Num',
            'Due Date',
            'High School',
            'Status',
            'Amount',
            'Billing Contact',
            'Billing Contact Email',
            'FileName'
        ])

        with zipfile.ZipFile(b, 'w') as zf:
            for record in records:
                row = []

                file_name = f'{record.number}.pdf'

                row.append(record.term)
                row.append(record.number)
                row.append(record.due_date)
                row.append(record.highschool.name)
                row.append(record.status)
                row.append(record.total_amount)
                row.append(record.billing_contact)
                row.append(record.billing_contact_email)
                row.append(file_name)

                writer.writerow(row)
                if data.get('export_invoices'):
                    pdf = record.as_pdf()
                    zf.writestr(file_name, pdf)

            # write export list file
            content = stream.getvalue()
            
            file_name = 'invoice-export.csv'
            zf.writestr(file_name, content)

            zf.close()

            response = HttpResponse(b.getvalue(), content_type="application/x-zip-compressed")
            response['Content-Disposition'] = f'attachment; filename={ZIPFILE_NAME}'
    
            path = media_storage.save(path_prefix+ZIPFILE_NAME, ContentFile(response.getvalue()))
            path = media_storage.url(path)

            return path
        
