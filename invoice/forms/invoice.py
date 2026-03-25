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

from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template import Context, Template
from django.template.loader import get_template, render_to_string

from cis.validators import validate_html_short_code, validate_cron

from form_fields import fields as FFields

from django_ckeditor_5.widgets import CKEditor5Widget as CKEditorWidget
from cis.models.customuser import CustomUser

from cis.models.term import Term
from cis.models.highschool import HighSchool
from cis.models.highschool_administrator import HSPosition

from cis.validators import validate_email_list
from cis.utils import YES_NO_OPTIONS
# from cis.models.section import StudentRegistration
from ..models import Invoice, InvoiceItem, InvoiceTemplate, InvoiceNote

from ..settings.invoice import invoice as InvoiceSettings

from ..views.applyde import ApplyDE

if getattr(settings, 'DEBUG'):
    try:
        from pd_event.pd_event.models import Event
    except:
        from pd_event.models import Event
else:
    from pd_event.models import Event
    
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

class InvoiceDeleteForm(forms.Form):
    ids = forms.MultipleChoiceField(
        required=False,
        label='Records to Delete',
        widget=forms.CheckboxSelectMultiple,
        choices=[]
    )

    action = forms.CharField(
        widget=forms.HiddenInput
    )

    def __init__(self, ids=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        configs = InvoiceSettings.from_db()

        self.fields['action'].initial = kwargs.get('action', 'delete_selected')
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

    def save(self, request=None):
        data = self.cleaned_data

        for regis_id in data.get('ids'):
            try:
                record = Invoice.objects.get(
                    id=regis_id
                )

                record.invoiceitem_set.all().delete()
                record.delete()
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

    event = forms.ModelMultipleChoiceField(
        queryset=None,
        required=True
    )

    term = forms.ModelChoiceField(
        queryset=None,
        required=True,
        label='Invoice Term'
    )

    highschool = forms.ModelChoiceField(
        queryset=HighSchool.objects.all(),
        required=False,
        label='High School',
        help_text='If you need to generate invoice for a single high school'
    )

    cost_per_attendee = forms.FloatField(
        label='Cost Per Attendee',
        required=False,
        help_text='Leave blank if cost is entered in the event details'
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
        help_text='Customize with {{highschool_name}}'
    )

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['term'].queryset = Term.objects.all().order_by('-code')
        self.fields['event'].queryset = Event.objects.all().order_by('-term__code', '-start_time')
        self.fields['billing_contact'].queryset = HSPosition.objects.all().order_by('name')
        self.fields['alt_billing_contact'].queryset = HSPosition.objects.all().order_by('name')

        self.fields['invoice_template'].queryset = InvoiceTemplate.objects.all().order_by('name')

        self.request = request

        self.helper = FormHelper()
        self.helper.form_class = 'frm_ajax'
        self.helper.form_id = 'frm_event_invoice'
        self.helper.form_method = 'POST'

    def save(self, request, commit=True):
        from collections import defaultdict

        data = self.cleaned_data

        highschools = defaultdict(lambda: defaultdict(list))
        for event in data.get('event'):
            for attendee in event.marked_as_attended:
                th = attendee.course_certificate.teacher_highschool
                hs = th.highschool

                if data.get('highschool') and data.get('highschool').id != hs.id:
                    continue

                highschools[hs.id][event.id].append(
                    f"{event.event_type.name} / {attendee.course_certificate.course.title} / {th.teacher.user.first_name} {th.teacher.user.last_name}"
                )

        for hsid, pd_events in highschools.items():
            highschool = HighSchool.objects.get(pk=hsid)
            description = Template(data.get('description')).render(Context({'highschool_name': highschool.name}))

            invoice = Invoice(
                due_date=data.get('due_date'),
                created_by=request.user,
                description=description,
                status='Draft',
                template=data.get('invoice_template'),
                term=data.get('term'),
                highschool=highschool,
                number=data.get('invoice_number') + highschool.code,
                meta={
                    'billing_contact_id': str(data.get('billing_contact').id),
                    'alt_billing_contact_id': str(data.get('alt_billing_contact').id),
                }
            )
            invoice.save()

            for event_id, teachers in pd_events.items():
                event = Event.objects.get(pk=event_id)

                for teacher in teachers:
                    InvoiceItem(
                        invoice=invoice,
                        amount=data.get('cost_per_attendee') or event.cost_per_attendee or 1000,
                        description=teacher,
                        created_by=request.user,
                    ).save()

        return


class ApplyDEInvoiceForm(forms.Form):
    from cis.models.section import StudentRegistration

    action = forms.CharField(
        required=True,
        widget=forms.HiddenInput,
        initial='applyde_registrations_invoice'
    )

    class_section_terms = forms.ChoiceField(
        choices=[],
        required=True,
        label='Class Section Term(s)'
    )

    lde_site_id = forms.CharField(
        required=False,
        label='LDE Site Code',
        help_text='Enter the LDE site code if applicable'
    )

    registration_status = forms.MultipleChoiceField(
        choices=(
            ('applied', 'Applied'),
            ('approved', 'Approved'),
            ('not_approved', 'Not Approved'),

            ('cancelled', 'Cancelled'),
            ('section_is_full', 'Section is Full'),
            ('waitlist', 'Waitlist'),
            ('late_application', 'Late Application'),

            ('registered', 'Registered'),
            ('drop', 'Dropped'),
            ('wd', 'Withdrawn'),
            ('app not processed', 'Application Not Processed-See Notes'),
        ),
        required=True,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input', 'id': 'registration_status_applyde'}),
        label='Registration Status to Include',
        help_text='Select all that apply'
    )

    cost_model = forms.ChoiceField(
        label='Cost Model',
        required=True,
        help_text='If cost per credit is selected, the cost will be calculated based on the number of credits for each course multiplied by rate set in the academic year. If cost per section is selected, the cost will be calculated based on the cost of each class section.',
        choices=[
            ('', 'Select Cost Model'),
            # ('cost_per_credit', 'Cost Per Credit'),
            ('cost_per_section', 'Cost Per Section')
        ]
    )

    bill_to = forms.ChoiceField(
        label='Bill To',
        required=True,
        choices=[
            ('class_section_highschool', 'Class Section High School'),
            ('student_highschool', 'Student High School')
        ]
    )

    line_item_grouping = forms.ChoiceField(
        choices=[
            ('', 'Select Line Item Grouping'),
            ('by_course', 'By Course'),
            ('by_student', 'By Student')
        ],
        label='Line Item Grouping',
        required=True,
        help_text='Select the line item grouping for this invoice. This will determine how the line items are grouped in the invoice.'
    )

    term = forms.ModelChoiceField(
        queryset=None,
        required=True,
        label='Invoice Term'
    )

    due_date = forms.DateField(
        label='Invoice Due Date'
    )
    
    invoice_template = forms.ModelChoiceField(
        queryset=None,
        label='Invoice Template',
        help_text='Select the invoice template to use for this invoice',
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
        help_text='Customize with {{highschool_name}}'
    )

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)

        apply_de = ApplyDE()

        self.fields['class_section_terms'].choices = apply_de.get_terms_pretty()

        terms = Term.objects.all().order_by('-code')
        self.fields['term'].queryset = terms
        # self.fields['courses'].queryset = Course.objects.all().order_by('name')
        # self.fields['highschools'].queryset = HighSchool.objects.all().order_by('name')

        self.fields['billing_contact'].queryset = HSPosition.objects.all().order_by('name')
        self.fields['alt_billing_contact'].queryset = HSPosition.objects.all().order_by('name')

        self.fields['invoice_template'].queryset = InvoiceTemplate.objects.all().order_by('name')

        self.request = request

        self.helper = FormHelper()
        self.helper.form_class = 'frm_ajax'
        self.helper.form_id = 'frm_add_new_applyde_registration_invoice'
        self.helper.form_method = 'POST'


    def save(self, request, commit=True):
        applyde = ApplyDE()

        from cis.models.section import StudentRegistration

        data = self.cleaned_data

        # get all the registrations for the selected class section terms
        registrations = applyde.get_registrations(
            term_id=data.get('class_section_terms'),
            sau=data.get('lde_site_id') if data.get('lde_site_id') != '' else None,
            group_by=data.get('line_item_grouping')
        )

        # print(registrations)
        highschools = {}
        for record in registrations:
            if data.get('bill_to') == 'student_highschool':
                if not highschools.get(record['student']['highschool']['sau']):
                    highschools[record['student']['highschool']['sau']] = []

                highschools[record['student']['highschool']['sau']].append(record)
            else:
                if not highschools.get(record['class_section']['highschool']['sau']):
                    highschools[record['class_section']['highschool']['sau']] = []

                highschools[record['class_section']['highschool']['sau']].append(record)

        for hsid, records in highschools.items():
        
            description = Template(data.get('description'))
            try:
                highschool = HighSchool.objects.get(state_code=hsid)
            except:
                continue

            context = Context({
                'highschool_name': highschool.name
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

            weight = 1
            current_item = previous_item = ''
            total_amount = total_number = 0
            for record in records:
                item = InvoiceItem(
                    invoice=invoice,
                    meta={
                        'padding': 'true'
                    }
                )

                # if data.get('cost_model') == 'cost_per_credit':
                #     item.amount = record['class_section']['course']['credit_hours'] * record['class_section']['term']['academic_year']['cost_per_credit']
                if data.get('cost_model') == 'cost_per_section':
                    item.amount = record['class_section']['tuition']

                if data.get('line_item_grouping') == 'by_student':
                    current_item = f"{record['student']['user']['last_name']}, {record['student']['user']['first_name']}"

                    if current_item != previous_item:
                        if previous_item != '':
                            header_item = InvoiceItem(
                                invoice=invoice,
                                amount=None,
                                created_by = request.user,
                                description=f'Total for {previous_item} - {total_number} classes ${total_amount:,.2f}',
                                weight=weight,
                                meta={
                                    'summary': 'true',
                                    'col1': f'Total for {previous_item} - {total_number} classes',
                                    'col2': f"${total_amount:.2f}",
                                }
                            )
                            header_item.save()
                            weight += 1

                            total_number = 0
                            total_amount = 0

                        header_item = InvoiceItem(
                            invoice=invoice,
                            amount=None,
                            created_by = request.user,
                            description=current_item,
                            weight=weight
                        )
                        header_item.save()
                        weight += 1


                    item.description = f"{record['class_section']['term']['label']}, {record['class_section']['course']['title']}"

                    previous_item = f"{record['student']['user']['last_name']}, {record['student']['user']['first_name']}"

                    total_number += 1
                    total_amount += item.amount
                else:
                    current_item = f"{record['class_section']['term']['label']}, {record['class_section']['course']['title']}"

                    if current_item != previous_item:

                        if previous_item != '':
                            header_item = InvoiceItem(
                                invoice=invoice,
                                amount=None,
                                created_by = request.user,
                                description=f'Total for {previous_item} - {total_number} students ${total_amount:,.2f}',
                                weight=weight,
                                meta={
                                    'summary': 'true',
                                    'col1': f'Total for {previous_item} - {total_number} students',
                                    'col2': f"${total_amount:,.2f}",
                                }
                            )
                            header_item.save()
                            weight += 1

                            total_number = 0
                            total_amount = 0

                        header_item = InvoiceItem(
                            invoice=invoice,
                            amount=None,
                            created_by = request.user,
                            description=current_item,
                            weight=weight
                        )
                        header_item.save()
                        weight += 1


                    item.description = f"{record['student']['user']['last_name']}, {record['student']['user']['first_name']}"

                    previous_item = f"{record['class_section']['term']['label']}, {record['class_section']['course']['title']}"

                    total_number += 1
                    total_amount += item.amount

                item.created_by = request.user
                item.weight = weight
                item.save()

                weight += 1

            if data.get('line_item_grouping') == 'by_student':
                header_item = InvoiceItem(
                    invoice=invoice,
                    amount=None,
                    created_by = request.user,
                    description=f'Total for {previous_item} - {total_number} classes ${total_amount:,.2f}',
                    weight=weight,
                    meta={
                        'summary': 'true',
                        'col1': f'Total for {previous_item} - {total_number} classes',
                        'col2': f"${total_amount:,.2f}",
                    }
                )
                header_item.save()
            else:
                header_item = InvoiceItem(
                    invoice=invoice,
                    amount=None,
                    created_by = request.user,
                    description=f'Total for {previous_item} - {total_number} students ${total_amount:,.2f}',
                    weight=weight,
                    meta={
                        'summary': 'true',
                        'col1': f'Total for {previous_item} - {total_number} students',
                        'col2': f"${total_amount:,.2f}",
                    }
                )
                header_item.save()
        return

class RegistrationsInvoiceForm(forms.Form):
    from cis.models.section import StudentRegistration

    action = forms.CharField(
        required=True,
        widget=forms.HiddenInput,
        initial='registrations_invoice'
    )

    class_section_terms = forms.ModelMultipleChoiceField(
        queryset=None,
        required=True,
        label='Class Section Term(s)'
    )

    courses = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False
    )

    highschools = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        label='Class Section High School(s)'
    )

    registration_status = forms.MultipleChoiceField(
        choices=StudentRegistration.STATUS_OPTIONS,
        required=True,
        widget=forms.CheckboxSelectMultiple,
        label='Registration Status to Include',
        help_text='Select all that apply'
    )

    pay_type = forms.MultipleChoiceField(
        required=False,
        label='Pay Type',
        choices=[('', 'All Pay Types')],
        widget=forms.CheckboxSelectMultiple
    )
    
    cost_model = forms.ChoiceField(
        label='Cost Model',
        required=True,
        help_text='If cost per credit is selected, the cost will be calculated based on the number of credits for each course multiplied by rate set in the academic year. If cost per section is selected, the cost will be calculated based on the cost of each class section.',
        choices=[
            ('', 'Select Cost Model'),
            ('cost_per_credit', 'Cost Per Credit'),
            ('cost_per_section', 'Cost Per Section')
        ]
    )

    bill_to = forms.ChoiceField(
        label='Bill To',
        required=True,
        choices=[
            ('class_section_highschool', 'Class Section High School'),
            ('student_highschool', 'Student High School')
        ]
    )

    line_item_grouping = forms.ChoiceField(
        choices=[
            ('', 'Select Line Item Grouping'),
            ('by_course', 'By Course'),
            ('by_student', 'By Student')
        ],
        label='Line Item Grouping',
        required=True,
        help_text='Select the line item grouping for this invoice. This will determine how the line items are grouped in the invoice.'
    )

    term = forms.ModelChoiceField(
        queryset=None,
        required=True,
        label='Invoice Term'
    )

    due_date = forms.DateField(
        label='Invoice Due Date'
    )
    
    invoice_template = forms.ModelChoiceField(
        queryset=None,
        label='Invoice Template',
        help_text='Select the invoice template to use for this invoice',
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
        help_text='Customize with {{highschool_name}}'
    )

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from cis.models.course import Course
        from cis.models.section import StudentRegistration

        terms = Term.objects.all().order_by('-code')
        self.fields['term'].queryset = terms
        self.fields['class_section_terms'].queryset = terms
        self.fields['courses'].queryset = Course.objects.all().order_by('name')
        self.fields['highschools'].queryset = HighSchool.objects.all().order_by('name')

        self.fields['billing_contact'].queryset = HSPosition.objects.all().order_by('name')
        self.fields['alt_billing_contact'].queryset = HSPosition.objects.all().order_by('name')

        self.fields['invoice_template'].queryset = InvoiceTemplate.objects.all().order_by('name')

        self.request = request

        self.helper = FormHelper()
        self.helper.form_class = 'frm_ajax'
        self.helper.form_id = 'frm_event_invoice'
        self.helper.form_method = 'POST'

        try:
            if StudentRegistration.PAY_OPTIONS:
                self.fields['pay_type'].choices = StudentRegistration.PAY_OPTIONS[1:]  # Exclude 'All Pay Types' option
        except AttributeError:
            pass

    def save(self, request, commit=True):
        from collections import defaultdict
        from cis.models.section import StudentRegistration

        data = self.cleaned_data
        by_student = data.get('line_item_grouping') == 'by_student'

        registrations = StudentRegistration.objects.filter(
            class_section__term__in=data.get('class_section_terms'),
            status__in=data.get('registration_status')
        )

        if data.get('pay_type'):
            registrations = registrations.filter(pay_type__in=data.get('pay_type'))

        if data.get('courses'):
            registrations = registrations.filter(class_section__course__in=data.get('courses'))

        if data.get('highschools'):
            registrations = registrations.filter(class_section__highschool__in=data.get('highschools'))

        if by_student:
            registrations = registrations.order_by(
                'student__user__last_name', 'student__user__first_name', 'class_section__term__code', 'class_section__course__name'
            )
        else:
            registrations = registrations.order_by(
                'class_section__term__code', 'class_section__course__name', 'student__user__last_name', 'student__user__first_name'
            )

        highschools = defaultdict(list)
        for record in registrations:
            hs = record.student.highschool if data.get('bill_to') == 'student_highschool' else record.class_section.highschool
            highschools[hs.id].append(record)

        for hsid, records in highschools.items():
            highschool = HighSchool.objects.get(pk=hsid)
            description = Template(data.get('description')).render(Context({'highschool_name': highschool.name}))

            invoice = Invoice(
                due_date=data.get('due_date'),
                created_by=request.user,
                description=description,
                status='Draft',
                template=data.get('invoice_template'),
                term=data.get('term'),
                highschool=highschool,
                number=data.get('invoice_number') + highschool.code,
                meta={
                    'billing_contact_id': str(data.get('billing_contact').id),
                    'alt_billing_contact_id': str(data.get('alt_billing_contact').id),
                }
            )
            invoice.save()

            weight = 1
            previous_item = ''
            total_amount = total_number = 0
            count_label = 'classes' if by_student else 'students'

            for record in records:
                item = InvoiceItem(invoice=invoice, meta={'padding': 'true'})

                if data.get('cost_model') == 'cost_per_credit':
                    item.amount = record.class_section.course.credit_hours * record.class_section.term.academic_year.cost_per_credit
                elif data.get('cost_model') == 'cost_per_section':
                    item.amount = getattr(record.class_section, 'cost', None) or getattr(record, 'billed_school_cost', None)

                if data.get('pay_type') and record.pay_type == 'school_partial' and record.pay_type in data.get('pay_type'):
                    item.amount = getattr(record, 'billed_school_cost', None)

                if by_student:
                    current_item = f'{record.student.user.last_name}, {record.student.user.first_name}'
                    item.description = f'{record.class_section.term}, {record.class_section.course.title}'
                else:
                    current_item = getattr(record.class_section, 'invoice_description', None) or f'{record.class_section.term}, {record.class_section.course.title}'
                    item.description = f'{record.student.user.last_name}, {record.student.user.first_name}'

                if current_item != previous_item:
                    if previous_item != '':
                        InvoiceItem(
                            invoice=invoice,
                            amount=None,
                            created_by=request.user,
                            description=f'Sub Total ${total_amount:,.2f}',
                            weight=weight,
                            meta={'summary': 'true', 'col1': 'Sub Total', 'col2': f'${total_amount:,.2f}'}
                        ).save()
                        weight += 1
                        total_number = 0
                        total_amount = 0

                    InvoiceItem(
                        invoice=invoice,
                        amount=None,
                        created_by=request.user,
                        description=current_item,
                        weight=weight
                    ).save()
                    weight += 1

                previous_item = current_item
                total_number += 1
                if item.amount:
                    total_amount += float(item.amount)

                item.created_by = request.user
                item.weight = weight
                item.save()
                weight += 1

            InvoiceItem(
                invoice=invoice,
                amount=None,
                created_by=request.user,
                description=f'Total for {previous_item} - {total_number} {count_label} ${total_amount:,.2f}',
                weight=weight,
                meta={
                    'summary': 'true',
                    'col1': f'Total for {previous_item} - {total_number} {count_label}',
                    'col2': f'${total_amount:,.2f}',
                }
            ).save()
        return

class InvoiceTemplateForm(forms.ModelForm):

    class Meta:
        model = InvoiceTemplate
        fields = '__all__'

        help_texts = {
            'description': 'Customize with {{invoice_term}}, {{invoice_amount}}, {{invoice_term}}, {{invoice_due_date}}, {{invoice_status}}, {{school_name}}, {{invoice_description}}, {{invoice_date}}, {{billing_contact_email}}, {{billing_contact_name}}, {{line_items}}',
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
        
        template = get_template('cis/email.html')
        html_body = template.render({
            'message': message,
            'tracking_url': invoice.tracking_url
        })

        # Create email
        email = EmailMultiAlternatives(
            subject=data.get('subject'),
            body=data.get("message"),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to
        )
        
        email.attach_alternative(html_body, "text/html")
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
    