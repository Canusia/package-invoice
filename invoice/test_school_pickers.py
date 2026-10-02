"""Campus-scoped school pickers on the invoice forms (cis HighSchoolCampus)."""
import datetime
import uuid

from django.conf import settings
from django.http import HttpRequest
from django.test import TestCase, override_settings

from cis.campus_context import campus_context
from cis.models.course import Campus
from cis.models.highschool import HighSchool, HighSchoolCampus

from .forms.invoice import (
    EventInvoiceForm, InvoiceForm, RegistrationsInvoiceForm)
from .models import Invoice


def _campus():
    return Campus.objects.create(
        name=f'C-{uuid.uuid4().hex[:8]}',
        code=f'{settings.CAMPUS_CODE_PREFIX}_{uuid.uuid4().hex[:6]}')


def _hs(name, campus=None, status='Active'):
    hs = HighSchool.objects.create(name=name, code=uuid.uuid4().hex[:8])
    HighSchoolCampus.objects.filter(highschool=hs).delete()
    if campus is not None:
        HighSchoolCampus.objects.create(
            highschool=hs, campus=campus, status=status)
    return hs


class _Base(TestCase):
    def setUp(self):
        self.a, self.b = _campus(), _campus()
        self.mine = _hs('Mine', self.a)
        self.foreign = _hs('Foreign', self.b)
        self.dormant = _hs('Dormant', self.a, 'Inactive')

    def _event_form(self, data=None):
        return EventInvoiceForm(HttpRequest(), data)

    def _registrations_form(self, data=None):
        return RegistrationsInvoiceForm(HttpRequest(), data)

    def _invoice_form(self, hs, data=None):
        invoice = Invoice(
            highschool=hs, due_date=datetime.date(2026, 1, 1), meta={})
        return InvoiceForm(data, instance=invoice)


@override_settings(MULTI_CAMPUS=True)
class MultiCampusTests(_Base):
    def test_event_form_excludes_other_campus(self):
        with campus_context(self.a):
            qs = self._event_form().fields['highschool'].queryset
            self.assertEqual(list(qs), [self.mine])

    def test_event_form_foreign_post_rejected(self):
        with campus_context(self.a):
            form = self._event_form({'highschool': str(self.foreign.pk)})
            form.is_valid()
            self.assertIn('highschool', form.errors)

    def test_event_form_is_evaluated_per_request(self):
        with campus_context(self.a):
            first = list(self._event_form().fields['highschool'].queryset)
        with campus_context(self.b):
            second = list(self._event_form().fields['highschool'].queryset)
        self.assertEqual(first, [self.mine])
        self.assertEqual(second, [self.foreign])

    def test_registrations_form_excludes_other_campus(self):
        with campus_context(self.a):
            qs = self._registrations_form().fields['highschools'].queryset
            self.assertEqual(list(qs), [self.mine])

    def test_registrations_form_foreign_post_rejected(self):
        with campus_context(self.a):
            form = self._registrations_form(
                {'highschools': [str(self.foreign.pk)]})
            form.is_valid()
            self.assertIn('highschools', form.errors)

    def test_invoice_form_excludes_other_campus(self):
        with campus_context(self.a):
            qs = self._invoice_form(None).fields['highschool'].queryset
            self.assertEqual(list(qs), [self.mine])

    def test_invoice_form_keeps_existing_school(self):
        # An invoice already billed to an inactive/other-campus school keeps it.
        for existing in (self.dormant, self.foreign):
            with campus_context(self.a):
                qs = self._invoice_form(existing).fields['highschool'].queryset
                self.assertEqual(
                    {h.pk for h in qs}, {self.mine.pk, existing.pk})

    def test_invoice_form_foreign_post_rejected(self):
        with campus_context(self.a):
            form = self._invoice_form(None, {'highschool': str(self.foreign.pk)})
            form.is_valid()
            self.assertIn('highschool', form.errors)


@override_settings(MULTI_CAMPUS=False)
class SingleCampusTests(_Base):
    def test_options_are_campus_linked_active_schools(self):
        with campus_context(self.a):
            self.assertEqual(
                list(self._event_form().fields['highschool'].queryset),
                [self.mine])
            self.assertEqual(
                list(self._registrations_form().fields['highschools'].queryset),
                [self.mine])
            self.assertEqual(
                list(self._invoice_form(None).fields['highschool'].queryset),
                [self.mine])
