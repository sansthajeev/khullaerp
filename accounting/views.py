from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import AccountGroup, Ledger, Voucher, VoucherEntry
from .forms import VoucherForm, VoucherEntryFormSet
from django.db import transaction, models
from django.core.exceptions import PermissionDenied
import json
import re
from django.apps import apps
from django.utils import timezone
from purchases.models import PurchaseInvoice, PurchaseInvoiceItem
from sales.models import Invoice, InvoiceItem

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

@login_required
def coa_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_group':
            name = request.POST.get('name')
            parent_id = request.POST.get('parent_id')
            if name:
                parent = AccountGroup.objects.get(id=parent_id) if parent_id else None
                AccountGroup.objects.create(name=name, parent=parent)
                messages.success(request, f"Account Group '{name}' created successfully.")
            return redirect('accounting:coa_list')
            
        elif action == 'add_ledger':
            name = request.POST.get('name')
            group_id = request.POST.get('group_id')
            account_type = request.POST.get('account_type')
            subledger_type = request.POST.get('subledger_type', 'None')
            opening_balance = request.POST.get('opening_balance', 0)
            
            if name and group_id and account_type:
                group = AccountGroup.objects.get(id=group_id)
                Ledger.objects.create(
                    name=name,
                    group=group,
                    account_type=account_type,
                    subledger_type=subledger_type,
                    opening_balance=opening_balance,
                    current_balance=opening_balance
                )
                messages.success(request, f"Ledger '{name}' created successfully.")
            return redirect('accounting:coa_list')
            
        elif action == 'delete_ledger':
            ledger_id = request.POST.get('ledger_id')
            if ledger_id:
                ledger = get_object_or_404(Ledger, id=ledger_id)
                if VoucherEntry.objects.filter(ledger=ledger).exists():
                    messages.error(request, f"Cannot delete '{ledger.name}' because it has existing transactions. Delete the associated vouchers first.")
                else:
                    ledger_name = ledger.name
                    ledger.delete()
                    messages.success(request, f"Ledger '{ledger_name}' was deleted successfully.")
            return redirect('accounting:coa_list')
            
        elif action == 'delete_group':
            group_id = request.POST.get('group_id')
            if group_id:
                group = get_object_or_404(AccountGroup, id=group_id)
                if Ledger.objects.filter(group=group).exists() or AccountGroup.objects.filter(parent=group).exists():
                    messages.error(request, f"Cannot delete '{group.name}' because it contains child groups or ledgers. Remove them first.")
                else:
                    group_name = group.name
                    group.delete()
                    messages.success(request, f"Account Group '{group_name}' was deleted successfully.")
            return redirect('accounting:coa_list')

    # Fetch root groups
    root_groups = AccountGroup.objects.filter(parent=None).order_by('code')
    all_groups = AccountGroup.objects.all().order_by('name')
    account_types = Ledger.ACCOUNT_TYPES
    subledger_choices = Ledger.SUBLEDGER_CHOICES
    
    return render(request, 'accounting/coa_list.html', {
        'root_groups': root_groups,
        'all_groups': all_groups,
        'account_types': account_types,
        'subledger_choices': subledger_choices
    })

@login_required
def ledger_edit_basic(request, pk):
    ledger = get_object_or_404(Ledger, pk=pk)
    if request.method == 'POST':
        ledger.subledger_type = request.POST.get('subledger_type', 'None')
        ledger.save()
        messages.success(request, f"Sub-ledger link for '{ledger.name}' updated to {ledger.subledger_type}.")
        return redirect('accounting:coa_list')
    return redirect('accounting:coa_list')

@login_required
def voucher_list(request):
    v_type = request.GET.get('type')
    vouchers = Voucher.objects.all().order_by('-date', '-id')
    if v_type:
        vouchers = vouchers.filter(voucher_type=v_type)
    return render(request, 'accounting/voucher_list.html', {
        'vouchers': vouchers,
        'current_type': v_type
    })

@login_required
def voucher_create(request, pk=None):
    voucher = None
    if pk:
        voucher = get_object_or_404(Voucher, pk=pk)
        v_type = voucher.voucher_type
    else:
        v_type = request.GET.get('type', 'Journal')

    if request.method == 'POST':
        form = VoucherForm(request.POST, instance=voucher)
        formset = VoucherEntryFormSet(request.POST, instance=voucher, prefix='entries')
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                voucher = form.save(commit=False)
                voucher.created_by = request.user
                voucher.save()
                
                # 1. Save line items from formset
                formset.instance = voucher
                formset.save()
                
                # 2. Add balancing entry if header ledger is provided (Special UX mode)
                cash_bank_ledger = form.cleaned_data.get('cash_bank_ledger')
                if cash_bank_ledger and voucher.voucher_type in ['Payment', 'Receipt']:
                    entries = voucher.entries.all()
                    total_debit = sum(e.debit for e in entries)
                    total_credit = sum(e.credit for e in entries)
                    diff = total_debit - total_credit
                    
                    if voucher.voucher_type == 'Payment' and diff > 0:
                        VoucherEntry.objects.create(voucher=voucher, ledger=cash_bank_ledger, credit=diff)
                    elif voucher.voucher_type == 'Receipt' and diff < 0:
                        VoucherEntry.objects.create(voucher=voucher, ledger=cash_bank_ledger, debit=abs(diff))
                
                # 3. Mark as finalized
                voucher.is_finalized = True
                voucher.save()
                
                msg = f"Voucher {voucher.number} updated successfully." if pk else f"Voucher {voucher.number} created successfully."
                messages.success(request, msg)
                return redirect('accounting:voucher_list')
    else:
        form = VoucherForm(instance=voucher, initial={'voucher_type': v_type})
        formset = VoucherEntryFormSet(instance=voucher, prefix='entries')
    
    # Ensure core ledgers exist before listing
    Ledger.ensure_core_ledgers()
    liquidity_ledgers = [l.id for l in Ledger.objects.all() if l.is_liquidity]
    
    # Identify sub-ledger types using explicit configuration
    ar_ap_ledgers = [l.id for l in Ledger.objects.filter(subledger_type='Contact')]
    payroll_ledgers = [l.id for l in Ledger.objects.filter(subledger_type='Employee')]
    
    return render(request, 'accounting/voucher_create.html', {
        'form': form,
        'formset': formset,
        'v_type': v_type,
        'pk': pk,
        'voucher': voucher,
        'liquidity_ledgers_json': json.dumps(liquidity_ledgers),
        'ar_ap_ledgers_json': json.dumps(ar_ap_ledgers),
        'payroll_ledgers_json': json.dumps(payroll_ledgers)
    })

@login_required
def voucher_delete(request, pk):
    if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'is_merchant', False)):
        raise PermissionDenied
    voucher = get_object_or_404(Voucher, pk=pk)
    if request.method == 'POST':
        with transaction.atomic():
            # 1. Attempt to delete linked Invoice/Purchase Bill
            narration = voucher.narration or ""
            if voucher.voucher_type == 'Sales':
                match = re.search(r'^Sales Invoice: ([\w\-]+)', narration)
                if match:
                    inv_num = match.group(1)
                    Invoice = apps.get_model('sales', 'Invoice')
                    Invoice.objects.filter(invoice_number=inv_num).delete()
            
            elif voucher.voucher_type == 'Purchase':
                match = re.search(r'^Purchase Bill: ([\w\-]+)', narration)
                if match:
                    bill_num = match.group(1)
                    PurchaseInvoice = apps.get_model('purchases', 'PurchaseInvoice')
                    PurchaseInvoice.objects.filter(bill_number=bill_num).delete()
            
            # 2. Delete the voucher itself
            voucher.delete()
            messages.success(request, f"Voucher {voucher.number} and any associated source document deleted.")
        return redirect('accounting:voucher_list')
    return render(request, 'accounting/voucher_confirm_delete.html', {'voucher': voucher})

@login_required
def voucher_detail(request, pk):
    voucher = get_object_or_404(Voucher, pk=pk)
    
    # Calculate totals for the template
    total_debit = sum(entry.debit for entry in voucher.entries.all())
    
    return render(request, 'accounting/voucher_detail.html', {
        'voucher': voucher,
        'total_amount': total_debit
    })

@login_required
def export_voucher_pdf(request, pk):
    voucher = get_object_or_404(Voucher, pk=pk)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Voucher_{voucher.number}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'VoucherTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor("#4f46e5"),
        alignment=1 # Center
    )
    
    label_style = ParagraphStyle(
        'LabelStyle',
        parent=styles['Normal'],
        fontSize=10,
        fontWeight='Bold',
        textColor=colors.grey
    )

    data_style = ParagraphStyle(
        'DataStyle',
        parent=styles['Normal'],
        fontSize=10,
        fontWeight='Bold'
    )

    # 1. Header Section
    elements.append(Paragraph(f"{voucher.voucher_type} VOUCHER", title_style))
    elements.append(Spacer(1, 10))

    # metadata table
    meta_data = [
        [Paragraph("Voucher Number:", label_style), Paragraph(voucher.number or "N/A", data_style), 
         Paragraph("Date (A.D.):", label_style), Paragraph(voucher.date.strftime('%Y-%m-%d') if voucher.date else "N/A", data_style)],
    ]
    
    # If it's payment or receipt, show the main account if possible
    # In the model, we don't store "cash_bank_ledger" directly on the voucher record as a separate field, 
    # it's just one of the entries. But if the view identifies it during creation, it's there.
    # For printing, we just show all entries.

    t_meta = Table(meta_data, colWidths=[1.2*inch, 2*inch, 1.2*inch, 2*inch])
    t_meta.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 20))

    # 2. Entries Table
    table_data = [
        ['Account Ledger', 'Sub-Ledger', 'Debit (DR)', 'Credit (CR)']
    ]
    
    total_dr = 0
    total_cr = 0
    
    for entry in voucher.entries.all():
        subledger = "N/A"
        if entry.contact: subledger = entry.contact.name
        elif entry.employee: subledger = entry.employee.name
        
        table_data.append([
            entry.ledger.name,
            subledger,
            f"{entry.debit:,.2f}" if entry.debit > 0 else "0.00",
            f"{entry.credit:,.2f}" if entry.credit > 0 else "0.00"
        ])
        total_dr += entry.debit
        total_cr += entry.credit

    # Total Row
    table_data.append(['TOTAL', '', f"{total_dr:,.2f}", f"{total_cr:,.2f}"])

    t = Table(table_data, colWidths=[2.5*inch, 1.5*inch, 1.2*inch, 1.2*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#475569")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f8fafc")),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
        ('TOPPADDING', (0, -1), (-1, -1), 10),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 30))

    # 3. Narration Section
    if voucher.narration:
        elements.append(Paragraph("Narration:", label_style))
        elements.append(Spacer(1, 5))
        elements.append(Paragraph(voucher.narration, styles['Normal']))
        elements.append(Spacer(1, 40))

    # 4. Signatures
    sig_data = [
        ['__________________', '__________________', '__________________'],
        ['Prepared By', 'Verified By', 'Approved By']
    ]
    t_sig = Table(sig_data, colWidths=[2.2*inch, 2.2*inch, 2.2*inch])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, 1), 9),
    ]))
    elements.append(t_sig)

    doc.build(elements)
    return response

@login_required
def voucher_edit(request, pk):
    if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'is_merchant', False)):
        raise PermissionDenied
    return voucher_create(request, pk=pk)


@login_required
def voucher_edit(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied
    return voucher_create(request, pk=pk)


# --- Reports Section ---

import datetime
import nepali_datetime
from django.db.models import Sum, Q

def get_report_dates(request):
    """Helper to parse AD/BS dates from request and return (from_date, to_date) in AD."""
    from_date_ad = request.GET.get('from_date_ad')
    to_date_ad = request.GET.get('to_date_ad')
    from_date_bs = request.GET.get('from_date_bs')
    to_date_bs = request.GET.get('to_date_bs')
    
    # Default to today if nothing provided
    today = datetime.date.today()
    start_of_month = today.replace(day=1)
    
    parsed_from = None
    parsed_to = None
    
    # 1. Check BS filters first (priority)
    if from_date_bs:
        try:
            parsed_from = nepali_datetime.datetime.strptime(from_date_bs, '%Y-%m-%d').to_datetime_date()
        except: pass
    elif from_date_ad:
        try:
            parsed_from = datetime.datetime.strptime(from_date_ad, '%Y-%m-%d').date()
        except: pass
        
    if to_date_bs:
        try:
            parsed_to = nepali_datetime.datetime.strptime(to_date_bs, '%Y-%m-%d').to_datetime_date()
        except: pass
    elif to_date_ad:
        try:
            parsed_to = datetime.datetime.strptime(to_date_ad, '%Y-%m-%d').date()
        except: pass
        
    return parsed_from or start_of_month, parsed_to or today

@login_required
def trial_balance(request):
    from_date, to_date = get_report_dates(request)
    ledgers = Ledger.objects.all().order_by('code')
    
    report_data = []
    total_opening_dr = 0
    total_opening_cr = 0
    total_period_dr = 0
    total_period_cr = 0
    total_closing_dr = 0
    total_closing_cr = 0
    
    for ledger in ledgers:
        # 1. Opening: Transactions BEFORE from_date
        open_agg = VoucherEntry.objects.filter(
            ledger=ledger, 
            voucher__date__lt=from_date
        ).aggregate(dr=Sum('debit'), cr=Sum('credit'))
        
        # Opening balance = Static Opening + (Dr - Cr) before from_date
        opening_net = ledger.opening_balance + ((open_agg.get('dr') or 0) - (open_agg.get('cr') or 0))
        
        # 2. Period: Transactions BETWEEN from_date AND to_date
        period_agg = VoucherEntry.objects.filter(
            ledger=ledger,
            voucher__date__gte=from_date,
            voucher__date__lte=to_date
        ).aggregate(dr=Sum('debit'), cr=Sum('credit'))
        
        p_dr = period_agg.get('dr') or 0
        p_cr = period_agg.get('cr') or 0
        
        # 3. Closing: Opening + Period Dr - Period Cr
        closing_net = opening_net + (p_dr - p_cr)
        
        # Totals for footer
        # Note: For Opening/Closing, we display Dr/Cr columns based on the Net position
        def get_dr_cr(net):
            if net > 0: return net, 0
            elif net < 0: return 0, abs(net)
            return 0, 0
            
        o_dr, o_cr = get_dr_cr(opening_net)
        c_dr, c_cr = get_dr_cr(closing_net)
        
        total_opening_dr += o_dr
        total_opening_cr += o_cr
        total_period_dr += p_dr
        total_period_cr += p_cr
        total_closing_dr += c_dr
        total_closing_cr += c_cr
        
        if opening_net != 0 or p_dr != 0 or p_cr != 0:
            report_data.append({
                'code': ledger.code,
                'name': ledger.name,
                'opening_dr': o_dr,
                'opening_cr': o_cr,
                'period_dr': p_dr,
                'period_cr': p_cr,
                'closing_dr': c_dr,
                'closing_cr': c_cr
            })
    
    return render(request, 'accounting/reports/trial_balance.html', {
        'report_data': report_data,
        'total_opening_dr': total_opening_dr,
        'total_opening_cr': total_opening_cr,
        'total_period_dr': total_period_dr,
        'total_period_cr': total_period_cr,
        'total_closing_dr': total_closing_dr,
        'total_closing_cr': total_closing_cr,
        'from_date': from_date,
        'to_date': to_date,
        'now': timezone.now()
    })


@login_required
def profit_loss(request):
    from_date, to_date = get_report_dates(request)
    
    # 1. Income ledgers
    income_ledgers = Ledger.objects.filter(account_type='Income')
    income_data = []
    total_income = 0
    
    for ledger in income_ledgers:
        # Movement within period
        mvmt = VoucherEntry.objects.filter(
            ledger=ledger,
            voucher__date__range=(from_date, to_date)
        ).aggregate(dr=Sum('debit'), cr=Sum('credit'))
        
        # Income increases with Credit
        val = (mvmt.get('cr') or 0) - (mvmt.get('dr') or 0)
        if val != 0:
            income_data.append({'name': ledger.name, 'balance': val})
            total_income += val
            
    # 2. Expense ledgers
    expense_ledgers = Ledger.objects.filter(account_type='Expense')
    expense_data = []
    total_expense = 0
    
    for ledger in expense_ledgers:
        mvmt = VoucherEntry.objects.filter(
            ledger=ledger,
            voucher__date__range=(from_date, to_date)
        ).aggregate(dr=Sum('debit'), cr=Sum('credit'))
        
        # Expense increases with Debit
        val = (mvmt.get('dr') or 0) - (mvmt.get('cr') or 0)
        if val != 0:
            expense_data.append({'name': ledger.name, 'balance': val})
            total_expense += val
            
    return render(request, 'accounting/reports/profit_loss.html', {
        'income_ledgers': income_data,
        'expense_ledgers': expense_data,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_profit': total_income - total_expense,
        'from_date': from_date,
        'to_date': to_date,
    })

@login_required
def balance_sheet(request):
    from_date, to_date = get_report_dates(request)
    
    def get_bal(ledger_qs, up_to):
        total = 0
        data = []
        for l in ledger_qs:
            mvmt = VoucherEntry.objects.filter(ledger=l, voucher__date__lte=up_to).aggregate(dr=Sum('debit'), cr=Sum('credit'))
            bal = l.opening_balance + (mvmt.get('dr') or 0) - (mvmt.get('cr') or 0)
            if bal != 0:
                # Flip for Liab/Equity display
                final_val = bal if l.account_type == 'Asset' else abs(bal)
                data.append({'name': l.name, 'current_balance': final_val})
                total += final_val
        return data, total

    assets_data, total_assets = get_bal(Ledger.objects.filter(account_type='Asset'), to_date)
    liabilities_data, total_liabilities = get_bal(Ledger.objects.filter(account_type='Liability'), to_date)
    equity_data, total_equity_base = get_bal(Ledger.objects.filter(account_type='Equity'), to_date)
    
    # Dynamic Net Profit (Cumulative up to to_date)
    inc_mvmt = VoucherEntry.objects.filter(ledger__account_type='Income', voucher__date__lte=to_date).aggregate(dr=Sum('debit'), cr=Sum('credit'))
    exp_mvmt = VoucherEntry.objects.filter(ledger__account_type='Expense', voucher__date__lte=to_date).aggregate(dr=Sum('debit'), cr=Sum('credit'))
    
    # Profit = Cr - Dr for Income - (Dr - Cr for Expense)
    # Actually simpler: Sum of all (Cr - Dr) for all types gives net profit if balanced.
    # We use: (Income Cr - Dr) - (Expense Dr - Cr)
    cum_profit = ((inc_mvmt.get('cr') or 0) - (inc_mvmt.get('dr') or 0)) - ((exp_mvmt.get('dr') or 0) - (exp_mvmt.get('cr') or 0))
    
    return render(request, 'accounting/reports/balance_sheet.html', {
        'assets': assets_data,
        'liabilities': liabilities_data,
        'equity': equity_data,
        'current_net_profit': cum_profit,
        'total_assets': total_assets,
        'total_liabilities_equity': total_liabilities + total_equity_base + cum_profit,
        'from_date': from_date,
        'to_date': to_date,
    })

@login_required
def cash_flow(request):
    from_date, to_date = get_report_dates(request)
    liquidity_ids = [l.id for l in Ledger.objects.all() if l.is_liquidity]
    
    cash_entries = VoucherEntry.objects.filter(
        ledger_id__in=liquidity_ids,
        voucher__date__range=(from_date, to_date)
    ).order_by('-voucher__date')
    
    total_inflow = sum(e.debit for e in cash_entries)
    total_outflow = sum(e.credit for e in cash_entries)
    
    return render(request, 'accounting/reports/cash_flow.html', {
        'entries': cash_entries,
        'total_inflow': total_inflow,
        'total_outflow': total_outflow,
        'net_cash_flow': total_inflow - total_outflow,
        'from_date': from_date,
        'to_date': to_date,
    })
from sales.models import Invoice
from purchases.models import PurchaseInvoice

@login_required
def sales_vat_report(request):
    from_date, to_date = get_report_dates(request)
    invoices = Invoice.objects.filter(
        date__range=(from_date, to_date),
        status='Finalized'
    ).order_by('date', 'invoice_number').select_related('customer')
    
    # In a real system, we'd distinguish taxable vs non-taxable line items.
    # For now, we assume all finalized invoices are taxable at 13% as per model defaults.
    # If some are 0%, we can aggregate InvoiceItem sums.
    
    total_taxable = 0
    total_vat = 0
    total_non_taxable = 0
    total_grand = 0
    
    report_data = []
    for inv in invoices:
        report_data.append({
            'date': inv.date,
            'number': inv.invoice_number,
            'party': inv.customer,
            'pan': inv.customer.pan_vat_number,
            'taxable': inv.sub_total,
            'non_taxable': 0, # Placeholder until multi-rate support
            'vat': inv.tax_amount,
            'total': inv.grand_total,
        })
        total_taxable += inv.sub_total
        total_vat += inv.tax_amount
        total_grand += inv.grand_total

    return render(request, 'accounting/reports/sales_vat_report.html', {
        'invoices': report_data,
        'from_date': from_date,
        'to_date': to_date,
        'total_taxable': total_taxable,
        'total_vat': total_vat,
        'total_grand': total_grand,
        'total_non_taxable': total_non_taxable,
    })

@login_required
def purchase_vat_report(request):
    from_date, to_date = get_report_dates(request)
    bills = PurchaseInvoice.objects.filter(
        date__range=(from_date, to_date),
        status='Finalized'
    ).order_by('date', 'bill_number').select_related('vendor')
    
    total_taxable = 0
    total_vat = 0
    total_non_taxable = 0
    total_grand = 0
    
    report_data = []
    for bill in bills:
        report_data.append({
            'date': bill.date,
            'number': bill.bill_number,
            'party': bill.vendor,
            'pan': bill.vendor.pan_vat_number,
            'taxable': bill.sub_total,
            'non_taxable': 0,
            'vat': bill.tax_amount,
            'total': bill.grand_total,
        })
        total_taxable += bill.sub_total
        total_vat += bill.tax_amount
        total_grand += bill.grand_total

    return render(request, 'accounting/reports/purchase_vat_report.html', {
        'bills': report_data,
        'from_date': from_date,
        'to_date': to_date,
        'total_taxable': total_taxable,
        'total_vat': total_vat,
        'total_grand': total_grand,
        'total_non_taxable': total_non_taxable,
    })

@login_required
def tds_report(request):
    from_date, to_date = get_report_dates(request)
    
    # 1. TDS Payable (from Purchases - aggregated from line items)
    purchases = PurchaseInvoice.objects.filter(
        date__range=(from_date, to_date),
        status='Finalized'
    ).annotate(
        total_tds=Sum('items__tds_amount')
    ).filter(
        total_tds__gt=0
    ).order_by('date', 'bill_number').select_related('vendor')
    
    # 2. TDS Receivable (from Sales - Decommissioned, only manual entries now)
    # Sales TDS has been removed from the Invoice model.
    sales = [] 
    
    total_payable = 0
    total_receivable = 0
    
    payables = []
    for p in purchases:
        # Note: rate might vary per item now, show 0 or "Multiple" in header-level summary if needed
        # For simplicity in the report, we calculate an effective rate or just show the total
        payables.append({
            'date': p.date,
            'number': p.bill_number,
            'party': p.vendor,
            'pan': p.vendor.pan_vat_number,
            'base_amount': p.sub_total,
            'rate': 0, # Could be multiple rates
            'amount': p.total_tds,
            'is_manual': False
        })
        total_payable += p.total_tds
        
    receivables = []
    # (Sales loop removed as it's decommissioned)

    # 3. Manual TDS Entries (from TDSJournalLine)
    from taxation.models import TDSJournalLine
    manual_entries = TDSJournalLine.objects.filter(
        tds_journal__voucher__date__range=(from_date, to_date),
        ledger__name='TDS Payable'
    ).select_related('tds_journal__voucher', 'ledger', 'taxable_ledger', 'tds_heading', 'employee', 'contact').order_by('tds_journal__voucher__date')
    
    for line in manual_entries:
        # Determine party name
        party_name = line.taxable_ledger.name if line.taxable_ledger else "Manual Journal"
        
        # Determine subledger details and PAN
        subledger = None
        pan = "N/A"
        if line.employee:
            subledger = line.employee.name
            pan = line.employee.pan_number or "N/A"
        elif line.contact:
            subledger = line.contact.name
            pan = line.contact.pan_vat_number or "N/A"
            
        row = {
            'date': line.tds_journal.voucher.date,
            'number': line.tds_journal.voucher.number,
            'party': party_name, # Sticking to 'party' to match template variable
            'party_name': party_name, # For fallback
            'subledger': subledger,
            'pan': pan,
            'base_amount': line.payment_amount,
            'rate': 0, # Could be from tds_heading if added later
            'amount': line.credit if line.credit > 0 else line.debit,
            'is_manual': True,
            'heading_code': line.tds_heading.code if line.tds_heading else "N/A",
            'heading_name': line.tds_heading.name if line.tds_heading else "N/A"
        }
        payables.append(row)
        total_payable += line.credit if line.credit > 0 else line.debit

    return render(request, 'accounting/reports/tds_report.html', {
        'payables': payables,
        'receivables': receivables,
        'from_date': from_date,
        'to_date': to_date,
        'total_payable': total_payable,
        'total_receivable': total_receivable,
    })


@login_required
def ledger_statement(request, ledger_id=None):
    from_date, to_date = get_report_dates(request)
    
    # 1. Selection logic
    selected_id = ledger_id or request.GET.get('ledger')
    ledgers = Ledger.objects.all().order_by('name')
    
    selected_ledger = None
    if selected_id:
        selected_ledger = get_object_or_404(Ledger, id=selected_id)
        
        # 2. Opening Balance CALCULATION
        aggregates_before = VoucherEntry.objects.filter(
            ledger=selected_ledger,
            voucher__date__lt=from_date
        ).aggregate(dr=Sum('debit'), cr=Sum('credit'))
        
        opening_from_transactions = (aggregates_before.get('dr') or 0) - (aggregates_before.get('cr') or 0)
        opening_balance = selected_ledger.opening_balance + opening_from_transactions
        
        # 3. Fetch Transactions in range
        entries = VoucherEntry.objects.filter(
            ledger=selected_ledger,
            voucher__date__gte=from_date,
            voucher__date__lte=to_date
        ).select_related('voucher').order_by('voucher__date', 'voucher__id')
        
        # 4. Calculate Running Balance
        current_running = opening_balance
        statement_data = []
        
        for entry in entries:
            current_running += (entry.debit - entry.credit)
            statement_data.append({
                'date': entry.voucher.date,
                'voucher_number': entry.voucher.number,
                'voucher_id': entry.voucher.id,
                'narration': entry.voucher.narration,
                'debit': entry.debit,
                'credit': entry.credit,
                'balance': current_running
            })
            
        closing_balance = current_running
    else:
        opening_balance = 0
        statement_data = []
        closing_balance = 0

    return render(request, 'accounting/reports/ledger_statement.html', {
        'ledgers': ledgers,
        'selected_ledger': selected_ledger,
        'from_date': from_date,
        'to_date': to_date,
        'opening_balance': opening_balance,
        'statement_data': statement_data,
        'closing_balance': closing_balance,
        'now': timezone.now()
    })

@login_required
def sales_register(request):
    from_date, to_date = get_report_dates(request)
    view_mode = request.GET.get('view_mode', 'itemwise')
    
    context = {
        'from_date': from_date,
        'to_date': to_date,
        'view_mode': view_mode,
        'total_qty': 0,
        'total_taxable': 0,
        'total_non_taxable': 0,
        'total_vat': 0,
        'total_grand': 0,
    }
    
    if view_mode == 'itemwise':
        items = InvoiceItem.objects.filter(
            invoice__date__range=(from_date, to_date),
            invoice__status='Finalized'
        ).select_related('invoice', 'invoice__customer', 'item').order_by('invoice__date', 'invoice__invoice_number')
        
        context['items'] = items
        for item in items:
            context['total_qty'] += item.quantity
            if item.tax_amount > 0:
                context['total_taxable'] += item.amount
            else:
                context['total_non_taxable'] += item.amount
            context['total_vat'] += item.tax_amount
            context['total_grand'] += (item.amount + item.tax_amount)
    else: # detailed
        invoices = Invoice.objects.filter(
            date__range=(from_date, to_date),
            status='Finalized'
        ).prefetch_related('items', 'items__item').select_related('customer').order_by('date', 'invoice_number')
        
        context['invoices'] = invoices
        for inv in invoices:
            inv.calc_taxable = 0
            inv.calc_non_taxable = 0
            for item in inv.items.all():
                context['total_qty'] += item.quantity
                if item.tax_amount > 0:
                    inv.calc_taxable += item.amount
                else:
                    inv.calc_non_taxable += item.amount
            context['total_taxable'] += inv.calc_taxable
            context['total_non_taxable'] += inv.calc_non_taxable
            context['total_vat'] += inv.tax_amount
            context['total_grand'] += inv.grand_total

    return render(request, 'accounting/reports/sales_register.html', context)

@login_required
def purchase_register(request):
    from_date, to_date = get_report_dates(request)
    view_mode = request.GET.get('view_mode', 'itemwise')
    
    context = {
        'from_date': from_date,
        'to_date': to_date,
        'view_mode': view_mode,
        'total_qty': 0,
        'total_taxable': 0,
        'total_non_taxable': 0,
        'total_vat': 0,
        'total_grand': 0,
    }
    
    if view_mode == 'itemwise':
        items = PurchaseInvoiceItem.objects.filter(
            purchase_invoice__date__range=(from_date, to_date),
            purchase_invoice__status='Finalized'
        ).select_related('purchase_invoice', 'purchase_invoice__vendor', 'item').order_by('purchase_invoice__date', 'purchase_invoice__bill_number')
        
        context['items'] = items
        for item in items:
            context['total_qty'] += item.quantity
            if item.tax_amount > 0:
                context['total_taxable'] += item.amount
            else:
                context['total_non_taxable'] += item.amount
            context['total_vat'] += item.tax_amount
            context['total_grand'] += (item.amount + item.tax_amount)
    else: # detailed
        invoices = PurchaseInvoice.objects.filter(
            date__range=(from_date, to_date),
            status='Finalized'
        ).prefetch_related('items', 'items__item').select_related('vendor').order_by('date', 'bill_number')
        
        context['invoices'] = invoices
        for inv in invoices:
            inv.calc_taxable = 0
            inv.calc_non_taxable = 0
            for item in inv.items.all():
                context['total_qty'] += item.quantity
                if item.tax_amount > 0:
                    inv.calc_taxable += item.amount
                else:
                    inv.calc_non_taxable += item.amount
            context['total_taxable'] += inv.calc_taxable
            context['total_non_taxable'] += inv.calc_non_taxable
            context['total_vat'] += inv.tax_amount
            context['total_grand'] += inv.grand_total

    return render(request, 'accounting/reports/purchase_register.html', context)
