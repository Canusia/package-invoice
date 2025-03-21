import csv, io, datetime
from django import forms
from django.conf import settings
from django.forms import ValidationError

from django.core.mail import EmailMessage

from io import BytesIO

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from django.template import Context, Template
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from cis.validators import validate_html_short_code, validate_cron

from form_fields import fields as FFields

from django_ckeditor_5.widgets import CKEditor5Widget as CKEditorWidget
from cis.models.customuser import CustomUser

from cis.models.term import Term
from cis.models.highschool import HighSchool
from cis.models.highschool_administrator import HSPosition

from cis.validators import validate_email_list
from cis.utils import YES_NO_OPTIONS
from ..models import Invoice, InvoiceItem, InvoiceTemplate, InvoiceNote

from ..settings.invoice import invoice as InvoiceSettings

class InvoiceChangeStatusForm(forms.Form):
    ids = forms.MultipleChoiceField(
        required=False,
        label='Records to Update',
        widget=forms.CheckboxSelectMultiple,
        choices=[]
    )
    
    new_status = forms.ChoiceField(
        required=True,
        label='Change Status To',
        choices=Invoice.STATUS_OPTIONS
    )

    action = forms.CharField(
        widget=forms.HiddenInput
    )

    def __init__(self, ids=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        configs = InvoiceSettings.from_db()

        self.fields['action'].initial = kwargs.get('action', 'update_status')
        if ids:
            invoices = Invoice.objects.filter(
                id__in=ids
            )

            invoice_choices = []
            for invoice in invoices:
                invoice_choices.append(
                    (
                        invoice.id,
                        f"{invoice.number} ({invoice.status})"
                    )
                )
            self.fields['ids'].choices = invoice_choices
            self.fields['ids'].initial = ids
        else:
            invoice_choices = []
            for regis_id in kwargs.get('data').getlist('ids'):
                invoice_choices.append(
                    (regis_id, regis_id)
                )

            self.fields['ids'].choices = invoice_choices
            self.fields['ids'].required = False

        if configs.get('status_notification_trigger'):
            self.fields['new_status'].help_text = 'Email will be sent when status is changed to ' + ', '.join(configs.get('status_notification_trigger', ['Not Set']))

    def save(self, request=None):
        data = self.cleaned_data

        new_status = data.get('new_status')
        for regis_id in data.get('ids'):
            try:
                record = Invoice.objects.get(
                    id=regis_id
                )

                record.status = new_status                
                record.save()                
            except Exception as e:
                print(e)

class EditLineItemForm(forms.Form):
    line_item_id = forms.CharField(
        widget=forms.HiddenInput
    )
        
    description = forms.CharField(
        required=True,
        help_text='',
        label='Description',
        widget=forms.Textarea
    )

    amount = forms.FloatField(
        required=True
    )

    action = forms.CharField(
        widget=forms.HiddenInput
    )

    def __init__(self, line_item, action, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if line_item:
            self.fields['line_item_id'].initial = line_item.id

            self.fields['description'].initial = line_item.description
            self.fields['amount'].initial = line_item.amount
        else:
            self.fields['line_item_id'].initial = "-1"

        self.fields['action'].initial = action

        self.helper = FormHelper()
        self.helper.form_class = 'frm_ajax'
        self.helper.form_id = 'frm_line_item'
        self.helper.form_method = 'POST'

    def clean(self):
        cleaned_data = super().clean()

        return cleaned_data

    def save(self, record, request=None):
        data = self.cleaned_data
        
        record.description = data.get('description')
        record.amount = data.get('amount')

        record.save()

        return record

class AddLineItemForm(forms.Form):
    invoice_id = forms.CharField(
        widget=forms.HiddenInput
    )
        
    description = forms.CharField(
        required=True,
        help_text='',
        label='Description',
        widget=forms.Textarea
    )

    amount = forms.FloatField(
        required=True
    )

    action = forms.CharField(
        widget=forms.HiddenInput
    )

    def __init__(self, invoice, action, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if invoice:
            self.fields['invoice_id'].initial = invoice.id
        
        self.fields['action'].initial = action

        self.helper = FormHelper()
        self.helper.form_class = 'frm_ajax'
        self.helper.form_id = 'frm_line_item'
        self.helper.form_method = 'POST'

    def clean(self):
        cleaned_data = super().clean()

        return cleaned_data

    def save(self, invoice, request=None):
        data = self.cleaned_data

        record = InvoiceItem(invoice=invoice)
        
        record.description = data.get('description')
        record.amount = data.get('amount')
        record.created_by = request.user

        record.save()

        return record
        

class EventInvoiceForm(forms.Form):
    action = forms.CharField(
        required=True,
        widget=forms.HiddenInput,
        initial='event_invoice'
    )

    event = forms.ModelChoiceField(
        queryset=None,
        required=True
    )

    term = forms.ModelChoiceField(
        queryset=None,
        required=True,
        label='Invoice Term'
    )

    cost_per_attendee = forms.FloatField(
        label='Cost Per Attendee'
    )
    
    due_date = forms.DateField(
        label='Due Date'
    )
    
    invoice_template = forms.ModelChoiceField(
        queryset=None,
        label='Invoice Template',
        required=True
    )
    
    billing_contact = forms.ModelChoiceField(
        queryset=None,
        label='Billing Contact Role'
    )

    alt_billing_contact = forms.ModelChoiceField(
        queryset=None,
        label='Alt Billing Contact Role'
    )

    invoice_number = forms.CharField(
        label='Invoice # Prefix',
        required=True
    )

    description = forms.CharField(
        widget=forms.Textarea,
        label='Invoice Description',
        help_text='Customize with {{highschool_name}}, {{event_term}}, {{event_type}}, {{event_date}}, {{event_course}}'
    )

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if getattr(settings, 'DEBUG'):
            from pd_event.pd_event.models import Event
        else:
            from pd_event.models import Event

        self.fields['term'].queryset = Term.objects.all().order_by('-code')
        self.fields['event'].queryset = Event.objects.all().order_by('-start_time')
        self.fields['billing_contact'].queryset = HSPosition.objects.all().order_by('name')
        self.fields['alt_billing_contact'].queryset = HSPosition.objects.all().order_by('name')

        self.fields['invoice_template'].queryset = InvoiceTemplate.objects.all().order_by('name')

        self.request = request

        self.helper = FormHelper()
        self.helper.form_class = 'frm_ajax'
        self.helper.form_id = 'frm_event_invoice'
        self.helper.form_method = 'POST'

    def save(self, request, commit=True):
        data = self.cleaned_data

        term = data.get('term')
        event = data.get('event')

        attendees = event.marked_as_attended

        highschools = {}
        for attendee in attendees:
            if not highschools.get(attendee.course_certificate.teacher_highschool.highschool.id):
                highschools[attendee.course_certificate.teacher_highschool.highschool.id] = {
                    'teachers': []
                }

            highschools[attendee.course_certificate.teacher_highschool.highschool.id]['teachers'].append(
                f"{attendee.course_certificate.teacher_highschool.teacher.user.first_name} {attendee.course_certificate.teacher_highschool.teacher.user.last_name}"
            )
        
        for hsid, teachers in highschools.items():
        
            description = Template(data.get('description'))
            highschool = HighSchool.objects.get(pk=hsid)

            context = Context({
                'highschool_name': highschool.name,
                'event_type': event.event_type.name,
                'event_term': event.term.label,
                'event_date': event.start_time.strftime('%m/%d/%Y'),
                'event_course': event.sexy_courses
            })

            description = description.render(context)

            invoice = Invoice()
            invoice.due_date = data.get('due_date')
            invoice.created_by = request.user
            invoice.description = description
            invoice.status = 'Draft'

            invoice.template = data.get('invoice_template')
            
            invoice.term = data.get('term')
            invoice.highschool = highschool
            invoice.number = data.get('invoice_number') + highschool.code

            invoice.meta = {}
            invoice.meta['billing_contact_id'] = str(data.get('billing_contact').id)
            invoice.meta['alt_billing_contact_id'] = str(data.get('alt_billing_contact').id)

            invoice.save()

            for teacher in teachers['teachers']:
                item = InvoiceItem(
                    invoice=invoice
                )
                
                item.amount = data.get('cost_per_attendee')
                item.description = teacher
                item.created_by = request.user
                
                item.save()

        return invoice


class InvoiceTemplateForm(forms.ModelForm):

    class Meta:
        model = InvoiceTemplate
        fields = '__all__'

        help_texts = {
            'description': 'Customize with {{invoice_term}}, {{invoice_amount}}, {{invoice_term}}, {{invoice_due_date}}, {{invoice_status}}, {{school_name}}, {{invoice_description}}'
        }

class EmailForm(forms.Form):
    
    action = forms.CharField(
        widget=forms.HiddenInput,
        initial='send_email'
    )

    invoice_id = forms.CharField(
        widget=forms.HiddenInput
    )

    to = forms.CharField(
        widget=forms.TextInput,
        validators=[validate_email_list],
        help_text='Comma separated email addresses'
    )

    subject = forms.CharField(
        widget=forms.TextInput,
    )

    message = forms.CharField(
        widget=forms.Textarea
    )

    attach_invoice = forms.BooleanField(
        label='Attach Invoice',
        required=False,
        help_text='Including attachment might get the email flagged as spam'
    )

    def __init__(self, invoice, action, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['invoice_id'].initial = invoice.id
        self.fields['action'].initial = action

        self.fields['to'].initial = invoice.billing_contact_email
        self.fields['attach_invoice'].label += f" {invoice.number} ({invoice.status})"
        
    def save(self, invoice, request):
        data = self.cleaned_data
        
        to = data.get('to', '').split(',')

        if getattr(settings, 'DEBUG'):
            to = ['kadaji@gmail.com']

        message = data.get('message').replace('\r\n', "<br>")
        message =+ invoice.tracking_url

        # Create email
        email = EmailMessage(
            subject=data.get('subject'),
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to
        )
        
        email.content_subtype = "html"

        if data.get('attach_invoice'):
            pdf = invoice.as_pdf()

            # Convert to BytesIO
            pdf_file = BytesIO(pdf)

            # Attach PDF file
            email.attach(f'invoice-{invoice.number}.pdf', pdf_file.getvalue(), 'application/pdf')

        # Send email
        email.send(fail_silently=True)

        invoice.add_note(request.user, f'Sent email to {data["to"]}<br>{data["message"]}<br>File Attached - {data["attach_invoice"]}')
        
class InvoiceNoteForm(forms.ModelForm):

    action = forms.CharField(
        widget=forms.HiddenInput
    )

    class Meta:
        model = InvoiceNote
        fields = [
            'note',
            'invoice'
        ]

        widgets = {
            'invoice': forms.HiddenInput
        }
    
    def __init__(self, invoice, action, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['invoice'].initial = invoice
        self.fields['action'].initial = action

    def save(self, request):
        data = self.cleaned_data

        record = super().save(commit=False)
        
        record.createdby = request.user
        record.meta = {'type': 'private'}

        record.save()

        return record
    
class InvoiceForm(forms.ModelForm):

    action = forms.CharField(
        widget=forms.HiddenInput,
        initial='edit_invoice_details'
    )

    due_date = forms.DateField(
        widget=forms.DateInput(format='%m/%d/%Y', attrs={'class':'col-md-6 col-sm-12'}),
        input_formats=[('%m/%d/%Y')]
    )

    billing_contact = forms.ModelChoiceField(
        queryset=None,
        label='Billing Contact Role'
    )

    alt_billing_contact = forms.ModelChoiceField(
        queryset=None,
        label='Alt Billing Contact Role'
    )

    total_amount = forms.FloatField(
        required=False,
        label='Total Amount',
        widget=forms.NumberInput(attrs={'readonly': 'readonly'}),
        help_text='Calculated Automatically'
    )

    class Meta:
        model = Invoice
        fields = [
            'number',
            'highschool',
            'term',
            'due_date',
            'description',
            'status',
            'template',
            # 'total_amount'
        ]
        
        
        labels = {
            'description': 'Description'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['description'].required = False

        instance = kwargs.get('instance')
        self.fields['due_date'].initial = instance.due_date.strftime('%m/%d/%Y')

        self.fields['billing_contact'].queryset = HSPosition.objects.all().order_by('name')
        self.fields['alt_billing_contact'].queryset = HSPosition.objects.all().order_by('name')

        self.fields['billing_contact'].initial = instance.meta.get('billing_contact_id')
        self.fields['alt_billing_contact'].initial = instance.meta.get('alt_billing_contact_id')

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Update'))

        if kwargs.get('instance'):
            self.fields['total_amount'].initial = kwargs.get('instance').total_amount

    def save(self):
        record = super().save()
        data = self.cleaned_data

        record.meta['billing_contact_id'] = str(data.get('billing_contact').id)
        record.meta['alt_billing_contact_id'] = str(data.get('alt_billing_contact').id)

        record.save()

        return record
    