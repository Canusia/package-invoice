MyCE - Invoice
====================
- Setup
In settings.py, add the app to INSTALLED_APPS as 
'invoice.apps.InvoiceConfig'

In myce.urls.py
- path('ce/invoices/', include('invoice.urls.ce'))

In Settings -> Menu add the menu items
{
    "type":"nav-item",
    "icon":"fas fa-fw fa-dollar-sign",
    "label":"Invoices",
    "name":"invoice",
    "sub_menu":[
        {
        "label":"All Invoices",
        "name":"all",
        "url":"invoice:all"
        },
        {
        "label":"PDF Templates",
        "name":"templates",
        "url":"invoice:invoice_templates"
        }
    ]
},