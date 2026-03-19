from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
import json
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.core.paginator import Paginator
from .models import TDSJournal, TDSJournalLine, TDSHeading
from .forms import TDSJournalForm, TDSJournalLineFormSet, TDSHeadingForm
from accounting.models import Ledger, Voucher, VoucherEntry
from hr.models import Employee
from contacts.models import Contact
from .utils import seed_default_tds_headings

@login_required
def tds_journal_list(request):
    journals = TDSJournal.objects.all().order_by('-voucher__date', '-voucher__number')
    return render(request, 'taxation/tds_journal_list.html', {'journals': journals})

@login_required
def tds_journal_create(request):
    employees = Employee.objects.filter(is_active=True)
    contacts = Contact.objects.all()
    headings = TDSHeading.objects.all().order_by('code')
    ledgers_qs = Ledger.objects.all().order_by('name').select_related('group')
    
    ledgers_data = []
    for l in ledgers_qs:
        ledgers_data.append({
            'id': l.id,
            'name': l.name,
            'code': l.code,
            'subledger_type': l.subledger_type,
            'is_tds': 'TDS' in l.name.upper() or 'TDS' in l.group.name.upper()
        })
    
    if request.method == 'POST':
        form = TDSJournalForm(request.POST)
        formset = TDSJournalLineFormSet(request.POST, prefix='tds_lines')
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # 1. Create the Accounting Voucher
                date = form.cleaned_data.get('date') or timezone.now().date()
                narration = form.cleaned_data.get('narration') or "TDS Journal Entry"
                
                voucher = Voucher.objects.create(
                    date=date,
                    voucher_type='Journal',
                    narration=narration,
                    created_by=request.user,
                    is_finalized=True # Tax journals are usually immediate
                )
                
                # 2. Create the TDS Journal Header
                tds_journal = TDSJournal.objects.create(voucher=voucher)
                
                # 3. Process Lines
                lines = formset.save(commit=False)
                for line in lines:
                    line.tds_journal = tds_journal
                    line.save()
                    
                    # 4. Create Voucher Entries
                    VoucherEntry.objects.create(
                        voucher=voucher,
                        ledger=line.ledger,
                        contact=line.contact,
                        employee=line.employee,
                        debit=line.debit,
                        credit=line.credit
                    )
                
                messages.success(request, f"TDS Journal {voucher.number} and accounting entries created successfully.")
                return redirect('taxation:tds_journal_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = TDSJournalForm(initial={'date': timezone.now().date()})
        formset = TDSJournalLineFormSet(prefix='tds_lines')
        
    existing_lines = []
    if request.method == 'POST':
        for form_item in formset:
            if form_item.cleaned_data or form_item.data:
                # We need to extract the data even if not yet cleaned
                existing_lines.append({
                    'id': form_item.instance.id if form_item.instance.id else f"old-{form_item.prefix}",
                    'ledger_id': form_item.data.get(f"{form_item.prefix}-ledger", ""),
                    'debit': float(form_item.data.get(f"{form_item.prefix}-debit", 0) or 0),
                    'credit': float(form_item.data.get(f"{form_item.prefix}-credit", 0) or 0),
                    'employee': form_item.data.get(f"{form_item.prefix}-employee", ""),
                    'contact': form_item.data.get(f"{form_item.prefix}-contact", ""),
                    'tds_heading': form_item.data.get(f"{form_item.prefix}-tds_heading", ""),
                    'taxable_ledger': form_item.data.get(f"{form_item.prefix}-taxable_ledger", ""),
                    'payment_amount': float(form_item.data.get(f"{form_item.prefix}-payment_amount", 0) or 0),
                    'subledger_type': form_item.data.get(f"{form_item.prefix}-subledger_type", "None"),
                    'deleted': form_item.data.get(f"{form_item.prefix}-DELETE") == 'on',
                    'errors': form_item.errors if form_item.errors else {}
                })

    return render(request, 'taxation/tds_journal_form.html', {
        'form': form,
        'formset': formset,
        'employees': employees,
        'contacts': contacts,
        'headings': headings,
        'ledgers': ledgers_qs,
        'ledgers_data': json.dumps(ledgers_data),
        'existing_lines': json.dumps(existing_lines)
    })

@login_required
def tds_journal_detail(request, pk):
    journal = get_object_or_404(TDSJournal, pk=pk)
    return render(request, 'taxation/tds_journal_detail.html', {'journal': journal})

@login_required
def tds_journal_edit(request, pk):
    if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'is_merchant', False)):
        raise PermissionDenied

    journal = get_object_or_404(TDSJournal, pk=pk)
    voucher = journal.voucher
    
    employees = Employee.objects.filter(is_active=True)
    contacts = Contact.objects.all()
    headings = TDSHeading.objects.all().order_by('code')
    ledgers_qs = Ledger.objects.all().order_by('name').select_related('group')
    
    ledgers_data = []
    for l in ledgers_qs:
        ledgers_data.append({
            'id': l.id,
            'name': l.name,
            'code': l.code,
            'subledger_type': l.subledger_type,
            'is_tds': 'TDS' in l.name.upper() or 'TDS' in l.group.name.upper()
        })
    
    if request.method == 'POST':
        form = TDSJournalForm(request.POST, instance=journal)
        formset = TDSJournalLineFormSet(request.POST, instance=journal, prefix='tds_lines')
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # 1. Update the Accounting Voucher
                date = form.cleaned_data.get('date') or timezone.now().date()
                narration = form.cleaned_data.get('narration') or "TDS Journal Entry"
                
                voucher.date = date
                voucher.narration = narration
                voucher.save()
                
                # 2. Save TDS Journal and Lines
                form.save()
                formset.save()
                
                # 3. Synchronize Voucher Entries
                # Simple approach: delete existing entries and recreate
                voucher.entries.all().delete()
                
                for line in journal.tds_lines.all():
                    VoucherEntry.objects.create(
                        voucher=voucher,
                        ledger=line.ledger,
                        contact=line.contact,
                        employee=line.employee,
                        debit=line.debit,
                        credit=line.credit
                    )
                
                messages.success(request, f"TDS Journal {voucher.number} updated successfully.")
                return redirect('taxation:tds_journal_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = TDSJournalForm(instance=journal, initial={'date': voucher.date, 'narration': voucher.narration})
        formset = TDSJournalLineFormSet(instance=journal, prefix='tds_lines')
        
    existing_lines = []
    # For edit mode, we populate from either the post data (if validation failed) or the actual database objects
    if request.method == 'POST':
        for form_item in formset:
            if form_item.cleaned_data or form_item.data:
                existing_lines.append({
                    'id': form_item.instance.id if form_item.instance.id else f"old-{form_item.prefix}",
                    'ledger_id': form_item.data.get(f"{form_item.prefix}-ledger", ""),
                    'debit': float(form_item.data.get(f"{form_item.prefix}-debit", 0) or 0),
                    'credit': float(form_item.data.get(f"{form_item.prefix}-credit", 0) or 0),
                    'employee': form_item.data.get(f"{form_item.prefix}-employee", ""),
                    'contact': form_item.data.get(f"{form_item.prefix}-contact", ""),
                    'tds_heading': form_item.data.get(f"{form_item.prefix}-tds_heading", ""),
                    'taxable_ledger': form_item.data.get(f"{form_item.prefix}-taxable_ledger", ""),
                    'payment_amount': float(form_item.data.get(f"{form_item.prefix}-payment_amount", 0) or 0),
                    'subledger_type': form_item.data.get(f"{form_item.prefix}-subledger_type", "None"),
                    'deleted': form_item.data.get(f"{form_item.prefix}-DELETE") == 'on',
                    'errors': form_item.errors if form_item.errors else {}
                })
    else:
        for line in journal.tds_lines.all():
            existing_lines.append({
                'id': line.id,
                'ledger_id': line.ledger.id,
                'debit': float(line.debit),
                'credit': float(line.credit),
                'employee': line.employee.id if line.employee else "",
                'contact': line.contact.id if line.contact else "",
                'tds_heading': line.tds_heading.id if line.tds_heading else "",
                'taxable_ledger': line.taxable_ledger.id if line.taxable_ledger else "",
                'payment_amount': float(line.payment_amount),
                'subledger_type': line.subledger_type,
                'deleted': False,
                'errors': {}
            })

    return render(request, 'taxation/tds_journal_form.html', {
        'form': form,
        'formset': formset,
        'employees': employees,
        'contacts': contacts,
        'headings': headings,
        'ledgers': ledgers_qs,
        'ledgers_data': json.dumps(ledgers_data),
        'existing_lines': json.dumps(existing_lines),
        'edit_mode': True
    })

@login_required
def tds_journal_delete(request, pk):
    if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'is_merchant', False)):
        raise PermissionDenied
    journal = get_object_or_404(TDSJournal, pk=pk)
    if request.method == "POST":
        journal.delete()
        messages.success(request, "TDS journal deleted.")
        return redirect('taxation:tds_journal_list')
    return render(request, 'taxation/tds_journal_confirm_delete.html', {'journal': journal})

@login_required
def tds_heading_list(request):
    query = request.GET.get('q', '')
    headings_list = TDSHeading.objects.all().order_by('code')
    
    if query:
        headings_list = headings_list.filter(
            Q(code__icontains=query) | Q(name__icontains=query)
        )
    
    paginator = Paginator(headings_list, 20)  # Show 20 headings per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'taxation/tds_heading_list.html', {
        'page_obj': page_obj,
        'query': query
    })

@login_required
def tds_heading_create(request):
    if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'is_merchant', False)):
        raise PermissionDenied
    
    if request.method == 'POST':
        form = TDSHeadingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "TDS Revenue Code created successfully.")
            return redirect('taxation:tds_heading_list')
    else:
        form = TDSHeadingForm()
    
    return render(request, 'taxation/tds_heading_form.html', {'form': form, 'title': 'Create TDS Revenue Code'})

@login_required
def tds_heading_edit(request, pk):
    if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'is_merchant', False)):
        raise PermissionDenied
    
    heading = get_object_or_404(TDSHeading, pk=pk)
    if request.method == 'POST':
        form = TDSHeadingForm(request.POST, instance=heading)
        if form.is_valid():
            form.save()
            messages.success(request, "TDS Revenue Code updated successfully.")
            return redirect('taxation:tds_heading_list')
    else:
        form = TDSHeadingForm(instance=heading)
    
    return render(request, 'taxation/tds_heading_form.html', {'form': form, 'title': 'Edit TDS Revenue Code'})

@login_required
def tds_heading_delete(request, pk):
    if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'is_merchant', False)):
        raise PermissionDenied
    
    heading = get_object_or_404(TDSHeading, pk=pk)
    # Check if used in any journal lines
    if heading.tds_lines.exists():
        messages.error(request, f"Cannot delete '{heading.code}' because it is used in TDS Journal entries.")
        return redirect('taxation:tds_heading_list')
        
    if request.method == 'POST':
        heading.delete()
        messages.success(request, "TDS Revenue Code deleted.")
        return redirect('taxation:tds_heading_list')
        
    return render(request, 'taxation/tds_heading_confirm_delete.html', {'heading': heading})

@login_required
def tds_headings_load_defaults(request):
    if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'is_merchant', False)):
        raise PermissionDenied
    
    seed_default_tds_headings()
    messages.success(request, "Standard IRD Revenue Codes have been loaded.")
    return redirect('taxation:tds_heading_list')

@login_required
def tds_heading_bulk_delete(request):
    if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'is_merchant', False)):
        raise PermissionDenied
    
    if request.method == 'POST':
        ids = request.POST.getlist('heading_ids')
        if not ids:
            messages.warning(request, "No headings selected for deletion.")
            return redirect('taxation:tds_heading_list')
        
        headings = TDSHeading.objects.filter(id__in=ids)
        deleted_count = 0
        skipped_count = 0
        
        for heading in headings:
            if heading.tds_lines.exists():
                skipped_count += 1
            else:
                heading.delete()
                deleted_count += 1
        
        if deleted_count:
            messages.success(request, f"Successfully deleted {deleted_count} revenue codes.")
        if skipped_count:
            messages.warning(request, f"Skipped {skipped_count} codes because they are used in transactions.")
            
    return redirect('taxation:tds_heading_list')
