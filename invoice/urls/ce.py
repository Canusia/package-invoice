from django.urls import path, include

from ..views.invoice import (
    index as invoices,
    detail as invoice,
    add_new as add_invoice,
    delete as delete_invoice,
    delete_line_item,
    event_info,
    do_bulk_action,
    as_pdf,
    InvoiceViewSet,
    InvoiceItemViewSet,
    InvoiceTemplateViewSet,
    InvoiceNoteViewSet,

    invoice_templates,
    invoice_template,

    track_email,
)
from rest_framework import routers

app_name = 'invoice'

router = routers.DefaultRouter()
router_viewsets = {
    'invoices': InvoiceViewSet,
    'invoice_items': InvoiceItemViewSet,

    'invoice_templates': InvoiceTemplateViewSet,
    'invoice_notes': InvoiceNoteViewSet,
}

for router_key in router_viewsets.keys():
    router.register(
        router_key,
        router_viewsets[router_key],
        basename=app_name
    )

from django.views.i18n import JavaScriptCatalog

urlpatterns = [
    path('api/', include(router.urls)),

    path('', invoices, name='all'),
    path('invoice/<uuid:record_id>/', invoice, name='invoice'),
    path('invoice/as_pdf/<uuid:record_id>/', as_pdf, name='as_pdf'),
    
    path('invoice/delete/<uuid:record_id>/', delete_invoice, name='delete_invoice'),
    path('invoice/line_item/delete/<uuid:record_id>/', delete_line_item, name='delete_line_item'),
    path('invoice/bulk_action/', do_bulk_action, name='bulk_action'),

    path('event_info/', event_info, name='event_info'),
    path('invoice_templates/', invoice_templates, name='invoice_templates'),
    path('invoice_template/<uuid:record_id>', invoice_template, name='invoice_template'),

    path('invoice/tracker/', track_email, name='track_email'),
]
