from django.contrib import admin
from .models import *  # Import all models from the app

# # Register your models here.
# for model in list(globals().values()):  # Use a copy of globals().values()
#     if isinstance(model, type) and issubclass(model, admin.ModelAdmin):
#         admin.site.register(model)

from .models import *


class InvoiceAdmin(admin.ModelAdmin):
    model = Invoice

class InvoiceItemAdmin(admin.ModelAdmin):
    model = InvoiceItem

class InvoiceTemplateAdmin(admin.ModelAdmin):
    model = InvoiceTemplate

admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(InvoiceItem, InvoiceItemAdmin)
admin.site.register(InvoiceTemplate, InvoiceTemplateAdmin)