# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Invoice management system for billing high schools. Generates invoices from PD events, student registrations, or ApplyDE data. Supports PDF generation, email notifications with tracking, and bulk operations.

## Key Components

### Models (`models.py`)
- **InvoiceTemplate** - Reusable invoice layouts with Django template syntax
- **Invoice** - Main invoice with highschool, term, status, line items
- **InvoiceItem** - Individual line items with amount and ordering
- **InvoiceNote** - Audit trail for changes and communications

### Invoice Status Flow
`Draft` → `Pending` → `Paid` or `Cancelled`

### URL Structure
- `/ce/invoices/` - Invoice list with DataTables
- `/ce/invoices/invoice/<uuid>/` - Detail/edit view
- `/ce/invoices/invoice/as_pdf/<uuid>/` - PDF download
- `/ce/invoices/invoice/tracker/` - Email open tracking pixel
- `/ce/invoices/api/` - REST endpoints for invoices, items, templates, notes

## Key Features

**PDF Generation:** Uses `pdfkit` with `wkhtmltopdf` backend.

**Email Tracking:** Injects tracking pixel, updates `meta['last_opened']` on open.

**Template Variables:** Invoice templates support Django syntax with context variables.

**Bulk Operations:** Status updates, deletions, email sends via `do_bulk_action` endpoint.

## Configuration

Via `invoice` settings form:
- `is_active` - Enable/disable emails (Yes/No/Debug)
- `status_notification_trigger` - Which statuses trigger emails
- Per-status email subject, body template, and PDF attachment toggle

## Signals (`signals.py`)
- **InvoiceItem post_save/delete:** Recalculates invoice total
- **Invoice post_save:** Triggers async notification if status matches trigger list

## Tasks (`tasks.py`)
```python
@task
def notify_invoice_update(invoice_id):
    # Async email notification via django-tasks
```

## Integration

- **HighSchool billing:** Links to `cis.HighSchool` and `HSAdministratorPosition` for billing contact
- **PD Events:** Can generate invoices from `pd_event.models.Event` attendance
- **ApplyDE:** External API integration for registration imports (`views/applyde.py`)
- **Storage:** Uses standard Django email with AWS SES
