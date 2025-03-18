MyCE - Invoice
====================

- Setup

In settings.py, add the app to INSTALLED_APPS as 
'invoice.apps.InvoiceConfig'

In myce.urls.py
- path('ce/invoices/', include('invoice.urls.ce'))

