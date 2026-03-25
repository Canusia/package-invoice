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

class HistoricalInvoiceSerializer(serializers.ModelSerializer):
    history_date = serializers.DateTimeField(format='%m/%d/%Y %I:%M %p')
    history_type_display = serializers.SerializerMethodField()
    changed_by = serializers.SerializerMethodField()

    def get_history_type_display(self, obj):
        return {'+': 'Created', '~': 'Changed', '-': 'Deleted'}.get(obj.history_type, obj.history_type)

    def get_changed_by(self, obj):
        if obj.history_user:
            return f'{obj.history_user.first_name} {obj.history_user.last_name}'
        return 'System'

    class Meta:
        model = Invoice.history.model
        fields = ['history_id', 'history_date', 'history_type_display', 'changed_by', 'status', 'number', 'total_amount']
        datatables_always_serialize = ['history_id']


class InvoiceSerializer(serializers.ModelSerializer):
    # invoice_item = InvoiceItemSerializer()
    term = TermSerializer()
    highschool = HighSchoolSerializer()

    ce_url = serializers.CharField()

    due_date = serializers.DateField(
        format='%m/%d/%Y'
    )

    status_changed_on = serializers.DateTimeField(
        format='%m/%d/%Y',
        allow_null=True
    )

    formatted_amount = serializers.CharField()
    billing_contact = serializers.CharField()
    
    class Meta:
        model = Invoice
        fields = '__all__'

        datatables_always_serialize = [
            'ce_url',
            'billing_contact',
            'status_changed_on',
        ]
