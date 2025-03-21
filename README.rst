MyCE - Invoice
====================
- Setup
In settings.py, 
    add the app to INSTALLED_APPS as 
        'invoice.apps.InvoiceConfig'

    Add path to STATIC_FILES_DIRS
        os.path.join(BASE_DIR, 'invoice', 'staticfiles'),

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

Include debounce in header-includes.html

<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery-throttle-debounce/1.1/jquery.ba-throttle-debounce.min.js" integrity="sha512-JZSo0h5TONFYmyLMqp8k4oPhuo6yNk9mHM+FY50aBjpypfofqtEWsAgRDQm94ImLCzSaHeqNvYuD9382CEn2zw==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>