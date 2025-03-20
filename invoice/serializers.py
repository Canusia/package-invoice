from django.contrib.auth import get_user_model

from rest_framework import serializers
from cis.models.course import Cohort

from cis.serializers.term import TermSerializer
from cis.serializers.highschool import HighSchoolSerializer
from cis.serializers.highschool_admin import CustomUserSerializer

from .models import (
    Invoice, InvoiceItem, InvoiceTemplate,
    InvoiceNote
)

class InvoiceItemSerializer(serializers.ModelSerializer):
    
    formatted_amount = serializers.CharField()

    class Meta:
        model = InvoiceItem
        fields = '__all__'

        datatables_always_serialize = [
            'id'
        ]

class InvoiceNoteSerializer(serializers.ModelSerializer):
    
    createdby = CustomUserSerializer()
    createdon = serializers.DateTimeField(format='%m/%d/%Y %I:%M %p')
    
    class Meta:
        model = InvoiceNote
        fields = '__all__'

        datatables_always_serialize = [
            'id'
        ]

class InvoiceTemplateSerializer(serializers.ModelSerializer):
    
    ce_url = serializers.CharField()

    class Meta:
        model = InvoiceTemplate
        fields = '__all__'

        datatables_always_serialize = [
            'ce_url',
        ]

class InvoiceSerializer(serializers.ModelSerializer):
    # invoice_item = InvoiceItemSerializer()
    term = TermSerializer()
    highschool = HighSchoolSerializer()

    ce_url = serializers.CharField()

    due_date = serializers.DateField(
        format='%m/%d/%Y'
    )
    
    formatted_amount = serializers.CharField()
    billing_contact = serializers.CharField()
    
    class Meta:
        model = Invoice
        fields = '__all__'

        datatables_always_serialize = [
            'ce_url',
            'billing_contact'
        ]
