import datetime, os, logging, csv

from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils import timezone

from django.utils.safestring import mark_safe

from django.template import Template, Context
from django.template.loader import get_template

from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from cis.models.faculty import FacultyCoordinator, FacultyCourseCoordinator
from cis.models.highschool import HighSchool
from cis.models.term import Term
from cis.models.course import Cohort, CohortParticipant, CohortAffiliation, Course, CourseAdministrator
from cis.models.note import EventNote
from cis.models.teacher import (
    TeacherCourseCertificate,
    Teacher
)

from ..forms.invoice import (
    EventInvoiceForm, InvoiceForm, InvoiceTemplateForm, InvoiceNoteForm,
    EmailForm,
    RegistrationsInvoiceForm,
    InvoiceChangeStatusForm
)

from ..models import Invoice, InvoiceItem, InvoiceTemplate, InvoiceNote
from ..serializers import (
    InvoiceItemSerializer, InvoiceSerializer, InvoiceTemplateSerializer,
    InvoiceNoteSerializer
)

from cis.menu import cis_menu, draw_menu, FACULTY_MENU

from cis.utils import CIS_user_only, user_has_faculty_role, FACULTY_user_only

class InvoiceNoteViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceNoteSerializer
    permission_classes = [CIS_user_only]

    def get_queryset(self):
        records = InvoiceNote.objects.all()

        if self.request.GET.get('invoice_id'):
            records = records.filter(
                invoice__id=self.request.GET.get('invoice_id')
            )

        return records

class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [CIS_user_only]

    def get_queryset(self):
        records = Invoice.objects.all()

        if self.request.GET.get('term'):
            records = records.filter(
                term__code=self.request.GET.get('term')
            )

        if self.request.GET.get('highschool'):
            records = records.filter(
                highschool__id=self.request.GET.get('highschool')
            )

        return records

class InvoiceItemViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceItemSerializer
    permission_classes = [CIS_user_only]

    def get_queryset(self):
        records = InvoiceItem.objects.all()

        if self.request.GET.get('invoice'):
            records = records.filter(
                invoice__id=self.request.GET.get('invoice')
            )

        return records
    
class InvoiceTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceTemplateSerializer
    permission_classes = [CIS_user_only]

    def get_queryset(self):
        records = InvoiceTemplate.objects.all()

        return records

@xframe_options_exempt
def detail(request, record_id):
    '''
    Record details page
    '''
    template = 'invoice/invoice.html'
    record = get_object_or_404(Invoice, pk=record_id)

    form = InvoiceForm(instance=record)
    
    if request.method == 'POST':

        if request.POST.get('action', '') == 'edit_invoice_details':
            form = InvoiceForm(instance=record, data=request.POST)

            if form.is_valid():
                record = form.save()

                return JsonResponse({
                    'status': 'success',
                    'message': 'Successfully updated invoice'
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Please fix the error(s) and try again',
                    'errors': form.errors.as_json()
                }, status=400)

    read_only = False
    menu = draw_menu(cis_menu, 'invoice', 'invoice', 'ce')
    urls = {
        'add_new': 'pd_event:event_add_new',
        'all_items': 'pd_event:events'
    }

    return render(
        request,
        template, {
            'form': form,
            'page_title': "Invoice",
            'labels': {
                'all_items': 'All Invoices'
            },

            'api_url': mark_safe(f'/ce/invoices/api/invoice_items?format=datatables&invoice={record.id}'),
            'notes_api_url': mark_safe(f'/ce/invoices/api/invoice_notes?format=datatables&invoice_id={record.id}'),
            'urls': urls,
            'read_only': read_only,
            'menu': menu,
            'record': record
        })

def add_new(request):
    ...

def delete(request, record_id):
    record = get_object_or_404(Invoice, pk=record_id)

    try:
        InvoiceItem.objects.filter(
            invoice=record
        ).delete()

        record.delete()

        data = {
            'status':'success',
            'message':'Success removed invoice',
        }
    except Exception as e:
        print(e)
        data = {
            'status':'error',
            'message':'You do not have permission to delete this record',
        }
    return JsonResponse(data)

def clone(request, record_id):
    record = get_object_or_404(Invoice, pk=record_id)

    try:
        cloned_record = record.clone()

        data = {
            'status':'success',
            'message':'Successfully cloned invoice. Click "Ok" to continue.',
            'redirect_url': cloned_record.ce_url
        }
    except Exception as e:
        data = {
            'status':'error',
            'message':'You do not have permission to clone this record',
        }
    return JsonResponse(data)

def delete_line_item(request, record_id):
    record = get_object_or_404(InvoiceItem, pk=record_id)

    try:        
        record.delete()

        data = {
            'status':'success',
            'message':'Success removed line item',
        }
    except Exception as e:
        data = {
            'status':'error',
            'message':'You do not have permission to delete this record',
        }
    return JsonResponse(data)


def do_bulk_action(request):
    action = request.GET.get('action')

    if request.method == 'POST':
        action = request.POST.get('action')
        
    if action == 'edit_line_item':
        return edit_line_item(request)
    
    if action == 'add_new_item':
        return add_new_item(request)
    
    if action == 'add_new_note':
        return add_new_note(request)
    
    if action == 'send_email':
        return send_email(request)
    
    if action == 'update_status':
        return update_status(request)


    data = {
        'status': 'success',
        'message': 'invalid action passed'
    }
    return JsonResponse(data)

def edit_line_item(request):
    template = 'invoice/bulk_action.html'

    from ..forms.invoice import EditLineItemForm
    if request.method == 'POST':
        id = request.POST.get('line_item_id')
        line_item = None

        if id != '-1':
            line_item = get_object_or_404(InvoiceItem, pk=id)

        form = EditLineItemForm(line_item, 'edit_line_item', data=request.POST)

        if form.is_valid():
            record = form.save(line_item)

            data = {
                'status':'success',
                'message':'Successfully updated record',
                'action': 'reload_table'
            }
            return JsonResponse(data)
        else:
            data = {
                'status':'error',
                'message':'Please correct the errors and try again.',
                'errors': form.errors.as_json()
            }
        return JsonResponse(data, status=400)

    ids = request.GET.getlist('ids[]')
    record = get_object_or_404(InvoiceItem, pk=ids[0])
    form = EditLineItemForm(record, 'edit_line_item')
    context = {
        'message': '',
        'title': 'Edit Line Item',
        'allow_delete': True,
        'form': form,
        'record': record
    }
    
    return render(request, template, context)

def update_status(request):
    template = 'invoice/bulk_action.html'

    if request.method == 'POST':

        form = InvoiceChangeStatusForm(data=request.POST)

        if form.is_valid():
            status = form.save()

            data = {
                'status':'success',
                'message':'Successfully updated records',
                'action': 'reload_table'
            }
            return JsonResponse(data)
        else:
            data = {
                'status':'error',
                'message':'Please correct the errors and try again.',
                'errors': form.errors.as_json()
            }
        return JsonResponse(data, status=400)

    ids = request.GET.getlist('ids[]')
    form = InvoiceChangeStatusForm(ids)
    context = {
        'title': 'Change Status',
        'message': '',
        'form': form
    }
    
    return render(request, template, context)

def add_new_item(request):
    template = 'invoice/bulk_action.html'

    from ..forms.invoice import AddLineItemForm
    if request.method == 'POST':
        id = request.POST.get('invoice_id')
        invoice = None

        if id != '-1':
            invoice = get_object_or_404(Invoice, pk=id)

        form = AddLineItemForm(invoice, 'add_new_item', data=request.POST)

        if form.is_valid():
            record = form.save(invoice,request)

            data = {
                'status':'success',
                'message':'Successfully added new line item',
                'action': 'reload_table'
            }
            return JsonResponse(data)
        else:
            data = {
                'status':'error',
                'message':'Please correct the errors and try again.',
                'errors': form.errors.as_json()
            }
        return JsonResponse(data, status=400)

    ids = request.GET.getlist('ids[]')
    record = get_object_or_404(Invoice, pk=ids[0])
    form = AddLineItemForm(record, 'add_new_item')
    context = {
        'message': '',
        'title': 'Add New Line Item',
        'allow_delete': False,
        'form': form,
        'record': None
    }
    
    return render(request, template, context)

def track_email(request):
    print(request.GET)
    invoice_id = request.GET.get('invoice')
    date = request.GET.get('date')

    try:
        invoice = Invoice.objects.filter(
            pk=invoice_id
        )
        if invoice:
            invoice = invoice[0]
            invoice.meta['last_opened'] = date
            invoice.save()

            invoice.add_note(None, f'Opened email sent on {date}')
    except:
        ...

    # Return a 1x1 transparent image
    response = HttpResponse(
        b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xFF\xFF\xFF\x00\x00\x00\x21\xF9\x04\x01\x00\x00\x00\x00\x2C\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4C\x01\x00\x3B',
        content_type="image/gif"
    )
    return response

track_email.login_required=False

def send_email(request):
    template = 'invoice/bulk_action.html'

    if request.method == 'POST':
        id = request.POST.get('invoice_id')
        invoice = None

        if id != '-1':
            invoice = get_object_or_404(Invoice, pk=id)

        form = EmailForm(invoice, 'send_email', data=request.POST)

        if form.is_valid():
            record = form.save(invoice, request)

            data = {
                'status':'success',
                'message':'Successfully sent email',
                'action': 'reload_table'
            }
            return JsonResponse(data)
        else:
            data = {
                'status':'error',
                'message':'Please correct the errors and try again.',
                'errors': form.errors.as_json()
            }
        return JsonResponse(data, status=400)

    ids = request.GET.getlist('ids[]')
    record = get_object_or_404(Invoice, pk=ids[0])
    form = EmailForm(record, 'send_email')
    context = {
        'message': '',
        'title': 'Send Email',
        'allow_delete': False,
        'form': form,
        'record': None
    }
    
    return render(request, template, context)

def add_new_note(request):
    template = 'invoice/bulk_action.html'

    if request.method == 'POST':
        id = request.POST.get('invoice')
        invoice = None

        if id != '-1':
            invoice = get_object_or_404(Invoice, pk=id)

        form = InvoiceNoteForm(invoice, 'add_new_item', data=request.POST)

        if form.is_valid():
            record = form.save(request)

            data = {
                'status':'success',
                'message':'Successfully added new note',
                'action': 'reload_table'
            }
            return JsonResponse(data)
        else:
            data = {
                'status':'error',
                'message':'Please correct the errors and try again.',
                'errors': form.errors.as_json()
            }
        return JsonResponse(data, status=400)

    ids = request.GET.getlist('ids[]')
    record = get_object_or_404(Invoice, pk=ids[0])
    form = InvoiceNoteForm(record, 'add_new_note')
    context = {
        'message': '',
        'title': 'Add New Note',
        'allow_delete': False,
        'form': form,
        'record': None
    }
    
    return render(request, template, context)

def event_info(request):

    if getattr(settings, 'DEBUG'):
        from pd_event.pd_event.models import Event
    else:
        from pd_event.models import Event

    if request.method == "GET":
        event_id = request.GET.get("event_id")  # Get selected product ID
        event = Event.objects.filter(id=event_id).first()
        if event:
            attended = event.marked_as_attended
            highschools = []

            for a in attended:
                if a.course_certificate.teacher_highschool.highschool.name not in highschools:
                    highschools.append(a.course_certificate.teacher_highschool.highschool.name)

            data = {
                "total_attended": attended.count(),
                "highschools": highschools
            }
            return JsonResponse(data)
        
    return JsonResponse({"error": "Event not found"}, status=404)


def as_pdf(request, record_id):
    from cis.settings.pd_event import pd_event as pd_settings

    record = get_object_or_404(Invoice, pk=record_id)

    if request.GET.get('print_only'):
        html = record.as_pdf('html')
        return HttpResponse(html)

    pdf = record.as_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    file_name = f"invoice-{record.number}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'

    return response


def index(request):
    '''
     search and index page for staff
    '''
    if request.method == 'POST':
        """
        Add New
        """
        if request.POST.get('action') == 'import_from_event':
            form = EventInvoiceForm(
                request=request,
                data=request.POST
            )

            if form.is_valid():
                record = form.save(request=request, commit=True)

                data = {
                    'status':'success',
                    'message':'Successfully added invoice(s). Click "Ok" to continue.',
                    'action': 'reload'
                }
                return JsonResponse(data)
            else:
                return JsonResponse({
                    'message': 'Please correct the errors and try again',
                    'errors': form.errors.as_json()
                }, status=400)
        elif request.POST.get('action') == 'registrations_invoice':
            form = RegistrationsInvoiceForm(
                request=request,
                data=request.POST
            )

            if form.is_valid():
                record = form.save(request=request, commit=True)

                data = {
                    'status':'success',
                    'message':'Successfully added invoice(s). Click "Ok" to continue.',
                    'action': 'reload'
                }
                return JsonResponse(data)
            else:
                return JsonResponse({
                    'message': 'Please correct the errors and try again',
                    'errors': form.errors.as_json()
                }, status=400)

    menu = draw_menu(cis_menu, 'invoice', 'all', 'ce')
    urls = {
        'add_new': 'pd_event:event_add_new',
        'details_prefix': '/ce/events/event/',
        'all_items': 'pd_event:event'
    }


    template = 'invoice/invoices.html'
    return render(
        request,
        template, {
            'page_title': 'Invoices',
            'urls': urls,
            'menu': menu,
            'import_from_event': EventInvoiceForm(request),
            'import_from_registrations': RegistrationsInvoiceForm(request),
            'terms': Term.objects.all().order_by('-code'),
            'api_url': '/ce/invoices/api/invoices?format=datatables'
        }
    )


@xframe_options_exempt
def invoice_template(request, record_id):
    '''
    Record details page
    '''
    template = 'invoice/invoice_template.html'
    record = get_object_or_404(InvoiceTemplate, pk=record_id)

    form = InvoiceTemplateForm(instance=record)
    
    if request.method == 'POST':

        if request.POST.get('action', '') == '':
            form = InvoiceTemplateForm(instance=record, data=request.POST)

            if form.is_valid():
                record = form.save()

                return JsonResponse({
                    'status': 'success',
                    'message': 'Successfully updated template'
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Please fix the error(s) and try again',
                    'errors': form.errors.as_json()
                }, status=400)

    read_only = False
    menu = draw_menu(cis_menu, 'invoice', 'invoice_template', 'ce')
    urls = {
        'add_new': 'pd_event:event_add_new',
        'all_items': 'pd_event:events'
    }

    return render(
        request,
        template, {
            'form': form,
            'page_title': "Invoice Template",
            'labels': {
                'all_items': 'All Invoices'
            },
            'urls': urls,
            'read_only': read_only,
            'menu': menu,
            'record': record
        })

def invoice_templates(request):
    '''
     search and index page for staff
    '''
    if request.method == 'POST':
        """
        Add New
        """
        form = InvoiceTemplateForm(
            data=request.POST
        )

        if form.is_valid():
            record = form.save(commit=True)

            data = {
                'status':'success',
                'message':'Successfully added template. Click "Ok" to continue.',
                'action': 'reload'
            }
            return JsonResponse(data)
        else:
            return JsonResponse({
                'message': 'Please correct the errors and try again',
                'errors': form.errors.as_json()
            }, status=400)


    menu = draw_menu(cis_menu, 'invoice', 'templates', 'ce')
    urls = {
        'add_new': 'pd_event:event_add_new',
        'details_prefix': '/ce/events/event/',
        'all_items': 'pd_event:event'
    }


    template = 'invoice/invoice_templates.html'
    return render(
        request,
        template, {
            'page_title': 'Invoice Templates',
            'urls': urls,
            'menu': menu,
            'import_from_event': InvoiceTemplateForm(),
            'api_url': '/ce/invoices/api/invoice_templates?format=datatables'
        }
    )
