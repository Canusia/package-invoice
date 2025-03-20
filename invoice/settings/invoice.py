import json
from django import forms
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.core.exceptions import ValidationError

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from cis.models.settings import Setting
from cis.validators import validate_html_short_code, validate_email_list

class SettingForm(forms.Form):

    STATUS_OPTIONS = [
        ('', 'Select'),
        ('Yes', 'Yes'),
        ('No', 'No'),
        ('Debug', 'Debug'),
    ]

    is_active = forms.ChoiceField(
        choices=STATUS_OPTIONS,
        label='Are Emails Enabled',
        help_text='',
        widget=forms.Select(attrs={'class': 'col-md-4 col-sm-12'}))

    debug_list = forms.CharField(
        label='Debug Recipient List',
        validators=[validate_email_list],
        help_text='If emails are in Debug mode they will be sent to the above address(es)',
        required=False
    )

    status_notification_trigger = forms.MultipleChoiceField(
        # choices=Invoice.STATUS_OPTIONS[1:],
        choices=[],
        required=False,
        label='Email - Status Trigger(s)',
        help_text='Status when notification is sent to billing contact',
        widget=forms.CheckboxSelectMultiple
    )

    def __init__(self, *args, **kwargs):

        from ..models import Invoice

        super().__init__(*args, **kwargs)

        self.fields['status_notification_trigger'].choices = Invoice.STATUS_OPTIONS[1:]
        
        for k, v in Invoice.STATUS_OPTIONS[1:]:
            self.fields[f"status_change_{k}_subject"] = forms.CharField(
                        widget=forms.TextInput,
                        help_text=f'{v} Subject',
                        required=False,
                        label=f'\'{v}\' Message Subject Line'
                    )
            
            self.fields[f"status_change_{k}_email"] = forms.CharField(
                        widget=forms.Textarea,
                        help_text='Message. Customize with {{invoice_term}}, {{invoice_amount}}, {{invoice_term}}, {{invoice_due_date}}, {{invoice_status}}, {{school_name}}, {{invoice_description}}.',
                        required=False,
                        label=f'\'{v}\' Message Email'
                    )
            
            self.fields[f"status_change_{k}_attach_invoice"] = forms.BooleanField(
                        required=False,
                        label=f'For \'{v}\' Attach Invoice in Email'
                    )
            
    def _to_python(self):
        """
        Return dict of form elements from $_POST
        """
        result = {}
        for key, value in self.cleaned_data.items():
            result[key] = value
        
        return result

class invoice(SettingForm):
    key = str(__name__)

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.request = request
        self.helper = FormHelper()
        self.helper.attrs = {'target':'_blank'}
        self.helper.form_method = 'POST'
        self.helper.form_action = reverse_lazy(
            'setting:run_record', args=[request.GET.get('report_id')])
        self.helper.add_input(Submit('submit', 'Save Setting'))

    def install(self):
        defaults = {            
        }

        try:
            setting = Setting.objects.get(key=self.key)
        except Setting.DoesNotExist:
            setting = Setting()
            setting.key = self.key

        setting.value = defaults
        setting.save()

    def preview(self, request, field_name):

        from django.template.loader import get_template, render_to_string
        from django.template import Context, Template
        from django.shortcuts import render, get_object_or_404

        if field_name in ['pd_template']:
            base_template = 'pd_event/base.html'
            pd_template = self.from_db().get('pd_template', '')
            
            pd_template = Template(pd_template)
            pd_html = pd_template.render(Context({
                'attendee_first_name': 'First Name',
                'attendee_last_name': 'Last Name',
                'cohort': 'Cohorts',
                'term': 'Term',
                'earned_pd_hour': '10',
                'start_date_time': '11/18/2018 12:02',
                'end_date_time': '12/01/1977 5:43',  
                'event_type': 'Event Type',
                'pd_note': 'PD Note',
                'delivery_mode': 'Del Mode',
                'description': "Description"
            }))

            return render(
                request,
                base_template,
                {'main_content': pd_html}
            )
        elif field_name in ['event_signin_template']:
            base_template = 'pd_event/base.html'
            pd_template = self.from_db().get('event_signin_template', '')
            
            attendee_list = render_to_string(
                'pd_event/event-attendee-list.html', {
                    'attendees': [
                        'Name 1', 'Name 2'
                    ]
                })

            pd_template = Template(pd_template)
            pd_html = pd_template.render(Context({
                'cohort': "Cohort Name",
                'term': "Term",
                'earned_pd_hour': "100",
                'start_date_time': "12/01/1977 05:43",
                'end_date_time': "11/18/2018 12:22",
                'event_type': "Event Type",
                'delivery_mode': "Delivery Mode",
                "guest_list": attendee_list,
                'pd_letter_url': "https://pd_letter_url",
            }))

            return render(
                request,
                base_template,
                {'main_content': pd_html}
            )
        elif field_name in ['pd_email_template']:
            email_settings = self.from_db()

            email = email_settings.get('pd_email_template')
            subject = email_settings.get('password_reset_subject')

            email_template = Template(email)
            context = Context({
                'attendee_first_name': request.user.first_name,
                'attendee_last_name': request.user.last_name,
                'cohort': "Cohort Name",
                'term': "Term",
                'earned_pd_hour': "100",
                'start_date_time': "12/01/1977 05:43",
                'end_date_time': "11/18/2018 12:22",
                'event_type': "Event Type",
                'delivery_mode': "Delivery Mode",
                'pd_letter_url': "https://pd_letter_url",
            })

            text_body = email_template.render(context)
            
            return render(
                request,
                'cis/email.html',
                {
                    'message': text_body
                }
            )

    @classmethod
    def from_db(cls):
        try:
            setting = Setting.objects.get(key=cls.key)
            return setting.value
        except Setting.DoesNotExist:
            return {}

    def run_record(self):
        try:
            setting = Setting.objects.get(key=self.key)
        except Setting.DoesNotExist:
            setting = Setting()
            setting.key = self.key

        setting.value = self._to_python()
        setting.save()

        return JsonResponse({
            'message': 'Successfully saved settings',
            'status': 'success'})
