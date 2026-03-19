from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import Invoice, InvoiceItem
from .forms import InvoiceForm, InvoiceItemFormSet
from accounting.models import Voucher, VoucherEntry, Ledger, AccountGroup
from inventory.models import Item
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from contacts.models import Contact
from django.utils import timezone
from decimal import Decimal

@login_required
def invoice_list(request):
    invoices = Invoice.objects.all().order_by('-date', '-created_at')
    return render(request, 'sales/invoice_list.html', {'invoices': invoices})

@login_required
def invoice_create(request):
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        formset = InvoiceItemFormSet(request.POST, prefix='items')
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                invoice = form.save(commit=False)
                invoice.created_by = request.user
                # The invoice.save() method will calculate discount_amount based on discount_type and discount_value
                invoice.save() 
                
                formset.instance = invoice
                formset.save()
                
                # Recalculate totals professionally
                sub_total = sum(item.amount for item in invoice.items.all())
                tax_total = sum(item.tax_amount for item in invoice.items.all())
                
                invoice.sub_total = sub_total
                invoice.tax_amount = tax_total
                # Grand total calculation is also in model save, but we do it here for precision
                # Ensure discount_amount is correctly applied after item totals are known
                invoice.grand_total = sub_total + tax_total - invoice.discount_amount
                invoice.save() # Save again to update sub_total, tax_total, grand_total
                
                if invoice.grand_total <= 0:
                    transaction.set_rollback(True)
                    messages.error(request, "Invoice total must be greater than zero.")
                else:
                    messages.success(request, f"Invoice {invoice.invoice_number} created successfully.")
                    return redirect('sales:invoice_detail', pk=invoice.pk)
    else:
        form = InvoiceForm()
        formset = InvoiceItemFormSet(prefix='items')
        
    items_data = {
        item.id: {
            'price': float(item.sales_price),
            'tax': float(item.tax_rate) if item.is_taxable else 0
        } for item in Item.objects.all()
    }
    
    return render(request, 'sales/invoice_create.html', {
        'form': form,
        'formset': formset,
        'items_data_json': json.dumps(items_data),
        'default_vat_rate': float(request.tenant.default_vat_rate) if request.tenant.is_vat_registered else 0
    })

@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    return render(request, 'sales/invoice_detail.html', {'invoice': invoice})

@login_required
def invoice_edit(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        formset = InvoiceItemFormSet(request.POST, instance=invoice, prefix='items')
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                invoice = form.save()
                formset.save()
                
                # Recalculate totals
                sub_total = 0
                tax_total = 0
                for item in invoice.items.all():
                    sub_total += item.amount
                    tax_total += item.tax_amount
                
                invoice.sub_total = sub_total
                invoice.tax_amount = tax_total
                invoice.grand_total = sub_total + tax_total - invoice.discount_amount
                invoice.save()
                
                if invoice.grand_total <= 0:
                    transaction.set_rollback(True)
                    messages.error(request, "Invoice total must be greater than zero.")
                else:
                    messages.success(request, f"Invoice {invoice.invoice_number} updated.")
                    return redirect('sales:invoice_detail', pk=invoice.pk)
    else:
        form = InvoiceForm(instance=invoice)
        formset = InvoiceItemFormSet(instance=invoice, prefix='items')
        
    items_data = {
        item.id: {
            'price': float(item.sales_price),
            'tax': float(item.tax_rate) if item.is_taxable else 0
        } for item in Item.objects.all()
    }
    
    return render(request, 'sales/invoice_create.html', {
        'form': form,
        'formset': formset,
        'is_edit': True,
        'invoice': invoice,
        'items_data_json': json.dumps(items_data),
        'default_vat_rate': float(request.tenant.default_vat_rate) if request.tenant.is_vat_registered else 0
    })

@login_required
def finalize_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if invoice.status != 'Draft':
        messages.error(request, "Only draft invoices can be finalized.")
        return redirect('sales:invoice_detail', pk=invoice.pk)
    
    if request.method == 'POST':
        with transaction.atomic():
            # 1. Ensure Ledgers
            Ledger.ensure_core_ledgers()
            ledger_sales = Ledger.objects.get(name='Local Sales')
            ledger_vat = Ledger.objects.get(name='Sales VAT (13%)')
            ledger_receivable = Ledger.objects.get(name='Accounts Receivable (General)')
            ledger_discount = Ledger.objects.get(name='Sales Discount Given')
            
            # 2. Create Voucher
            voucher = Voucher.objects.create(
                date=invoice.date,
                voucher_type='Sales',
                narration=f"Sales Invoice: {invoice.invoice_number} for {invoice.customer.name}",
                created_by=request.user,
                is_finalized=True
            )
            
            # 3. Double Entry
            # Debit Accounts Receivable (Total)
            VoucherEntry.objects.create(
                voucher=voucher,
                ledger=ledger_receivable,
                debit=invoice.grand_total
            )
            
            # Debit Discount Given (if any)
            if invoice.discount_amount > 0:
                VoucherEntry.objects.create(
                    voucher=voucher,
                    ledger=ledger_discount,
                    debit=invoice.discount_amount
                )
            
            # Group sales revenue by specific Item Ledgers or Default Sales Ledger
            sales_ledger_totals = {}
            for line in invoice.items.all():
                ledger = line.item.sales_account if line.item.sales_account else ledger_sales
                if ledger not in sales_ledger_totals:
                    sales_ledger_totals[ledger] = 0
                sales_ledger_totals[ledger] += line.amount

            # Credit the respective Sales/Income ledgers
            for ledger, amount in sales_ledger_totals.items():
                if amount > 0:
                    VoucherEntry.objects.create(
                        voucher=voucher,
                        ledger=ledger,
                        credit=amount
                    )
            
            # Credit Sales VAT (Tax)
            if invoice.tax_amount > 0:
                VoucherEntry.objects.create(
                    voucher=voucher,
                    ledger=ledger_vat,
                    credit=invoice.tax_amount
                )
            
            # 4. Integrate Stock (Deduct sold quantities for Goods)
            for line in invoice.items.all():
                item = line.item
                if item.item_type == 'Goods':
                    item.current_stock -= line.quantity
                    item.save()
            
            # 5. Finalize Invoice
            invoice.status = 'Finalized'
            invoice.save()
            
            messages.success(request, f"Invoice {invoice.invoice_number} has been finalized. Accounting entries and stock levels updated.")
            
    return redirect('sales:invoice_detail', pk=invoice.pk)
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

@login_required
def export_invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{invoice.invoice_number}.pdf"'

    # Page settings
    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    # Custom premium styles
    title_style = ParagraphStyle(
        'InvoiceTitle', parent=styles['Heading1'], fontSize=20, 
        textColor=colors.HexColor("#4f46e5"), spaceAfter=10, 
        fontWeight='Bold', alignment=0
    )
    
    label_style = ParagraphStyle(
        'LabelStyle', parent=styles['Normal'], fontSize=9, 
        textColor=colors.grey, fontWeight='Bold', spaceAfter=2
    )
    
    data_style = ParagraphStyle(
        'DataStyle', parent=styles['Normal'], fontSize=10, 
        fontWeight='Bold', spaceAfter=10
    )

    item_header_style = ParagraphStyle(
        'ItemHeader', parent=styles['Normal'], fontSize=9, 
        fontWeight='Bold', textColor=colors.HexColor("#475569")
    )

    # 1. Header & Brand Section
    header_data = [
        [Paragraph("Khullaerp", title_style), Paragraph(f"INVOICE", ParagraphStyle('InvLabel', parent=styles['Heading1'], fontSize=24, textColor=colors.grey, alignment=2))],
        [Paragraph("Digital Solution for Modern Business", ParagraphStyle('Sub', parent=styles['Normal'], fontSize=9, textColor=colors.grey)), Paragraph(f"#{invoice.invoice_number}", ParagraphStyle('InvNum', parent=styles['Normal'], fontSize=14, fontWeight='Bold', alignment=2, textColor=colors.HexColor("#4f46e5")))]
    ]
    t_header = Table(header_data, colWidths=[3.5*inch, 3.5*inch])
    t_header.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(t_header)
    elements.append(Spacer(1, 30))

    # 2. Billed To & Dates
    billing_data = [
        [Paragraph("BILLED TO", label_style), "", Paragraph("INVOICE DATE", label_style), Paragraph("DUE DATE", label_style)],
        [Paragraph(invoice.customer.name, data_style), "", Paragraph(invoice.date.strftime('%Y-%m-%d'), data_style), Paragraph(invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else "Prompt", data_style)],
        [Paragraph(invoice.customer.address or "Address not provided", ParagraphStyle('Addr', parent=styles['Normal'], fontSize=9)), "", "", ""]
    ]
    t_bill = Table(billing_data, colWidths=[2.5*inch, 2*inch, 1.25*inch, 1.25*inch])
    t_bill.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(t_bill)
    elements.append(Spacer(1, 40))

    # 3. Items Table
    table_data = [
        [Paragraph("Description", item_header_style), Paragraph("Qty", item_header_style), Paragraph("Rate", item_header_style), Paragraph("Tax %", item_header_style), Paragraph("Total", item_header_style)]
    ]
    
    for item in invoice.items.all():
        table_data.append([
            Paragraph(f"<b>{item.item.name}</b><br/><font size='8' color='grey'>{item.description or ''}</font>", styles['Normal']),
            str(item.quantity),
            f"{item.unit_price:,.2f}",
            f"{item.tax_rate}%",
            f"{(item.amount + item.tax_amount):,.2f}"
        ])

    t = Table(table_data, colWidths=[3*inch, 0.7*inch, 1.1*inch, 0.7*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#475569")),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.1, colors.HexColor("#e2e8f0")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#fbfcfe")]),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 30))

    # 4. Summary Section
    summary_data = [
        ["", "Sub-Total:", f"NPR {invoice.sub_total:,.2f}"],
        ["", "VAT Total:", f"NPR {invoice.tax_amount:,.2f}"],
        ["", "Total Discount:", f"- NPR {invoice.discount_amount:,.2f}"],
        ["", Paragraph("GRAND TOTAL", ParagraphStyle('GT', parent=styles['Normal'], fontSize=12, fontWeight='Bold', textColor=colors.HexColor("#4f46e5"))), 
             Paragraph(f"NPR {invoice.grand_total:,.2f}", ParagraphStyle('GTval', parent=styles['Normal'], fontSize=12, fontWeight='Bold', textColor=colors.HexColor("#4f46e5"), alignment=2))]
    ]
    t_summary = Table(summary_data, colWidths=[4*inch, 1.5*inch, 1.5*inch])
    t_summary.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTNAME', (1, 0), (1, -2), 'Helvetica'),
        ('FONTNAME', (1, -1), (2, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (2, 2), (2, 2), colors.HexColor("#ef4444")),
        ('LINEBELOW', (1, -2), (2, -2), 1, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (1, -1), (2, -1), 10),
    ]))
    elements.append(t_summary)

    # 5. Notes & Footer
    if invoice.notes:
        elements.append(Spacer(1, 40))
        elements.append(Paragraph("TERMS & NOTES", label_style))
        elements.append(Paragraph(invoice.notes, ParagraphStyle('Notes', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor("#64748b"))))

    elements.append(Spacer(1, 60))
    elements.append(Paragraph("This is a computer-generated document and requires no physical signature.", 
                              ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=1)))

    doc.build(elements)
    return response

@login_required
def invoice_delete(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        with transaction.atomic():
            # Also find and delete the linked voucher if it exists
            Voucher.objects.filter(narration__contains=f"Sales Invoice: {invoice.invoice_number}").delete()
            invoice.delete()
            messages.success(request, f"Invoice {invoice.invoice_number} and associated accounting records deleted.")
        return redirect('sales:invoice_list')
    return render(request, 'sales/invoice_confirm_delete.html', {'invoice': invoice})

# --- POS System ---

@login_required
def pos_view(request):
    """Renders the main POS interface."""
    walkin_customer, created = Contact.objects.get_or_create(
        name="Walk-in Customer",
        defaults={'contact_type': 'Customer'}
    )
    
    # Fetch all customers for the selection list
    customers = Contact.objects.filter(contact_type='Customer').order_by('name')
    
    # Fetch some initial items for the "Quick Selection" grid
    # We can fetch top 12 items by default
    initial_items = Item.objects.all()[:12]
    
    return render(request, 'sales/pos.html', {
        'walkin_customer_id': walkin_customer.id,
        'customers': customers,
        'customers_json': json.dumps([{'id': c.id, 'name': c.name, 'phone': c.phone or ''} for c in customers]),
        'initial_items': initial_items
    })

@login_required
def pos_item_search(request):
    """JSON search for items by name or SKU/barcode."""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    # Use Q objects for complex queries
    from django.db.models import Q
    items = Item.objects.filter(
        Q(name__icontains=query) | 
        Q(sku__icontains=query) |
        Q(barcode__icontains=query)
    )[:10]
    
    results = []
    for item in items:
        results.append({
            'id': item.id,
            'name': item.name,
            'sku': item.sku,
            'barcode': item.barcode,
            'price': float(item.sales_price),
            'stock': float(item.current_stock),
            'tax_rate': float(item.tax_rate) if item.is_taxable else 0,
            'uom': item.uom.short_name
        })
    
    return JsonResponse({'results': results})

@login_required
@require_POST
def pos_submit(request):
    """Process a POS order from JSON data."""
    try:
        data = json.loads(request.body)
        items_data = data.get('items', [])
        customer_id = data.get('customer_id')
        payment_method = data.get('payment_method', 'Cash')
        
        if not items_data:
            return JsonResponse({'success': False, 'message': 'Cart is empty.'})
            
        with transaction.atomic():
            customer = Contact.objects.get(pk=customer_id)
            
            # 1. Create Invoice
            invoice = Invoice.objects.create(
                customer=customer,
                date=timezone.now().date(),
                status='Draft',
                created_by=request.user,
                notes=f"POS Sale - Paid via {payment_method}"
            )
            
            sub_total = Decimal('0.00')
            tax_total = Decimal('0.00')
            
            for line in items_data:
                item = Item.objects.get(pk=line['item_id'])
                qty = Decimal(str(line['qty']))
                price = Decimal(str(line['price']))
                tax_rate = item.tax_rate if item.is_taxable else Decimal('0.00')
                
                invoice_item = InvoiceItem.objects.create(
                    invoice=invoice,
                    item=item,
                    quantity=qty,
                    unit_price=price,
                    tax_rate=tax_rate
                )
                sub_total += invoice_item.amount
                tax_total += invoice_item.tax_amount
                
            invoice.sub_total = sub_total
            invoice.tax_amount = tax_total
            invoice.grand_total = sub_total + tax_total
            invoice.save()
            
            # 2. Finalize
            Ledger.ensure_core_ledgers()
            ledger_sales = Ledger.objects.get(name='Local Sales')
            ledger_vat = Ledger.objects.get(name='Sales VAT (13%)')
            
            if payment_method == 'Bank':
                payment_ledger = Ledger.objects.get(name='Bank Account (POS)')
            else:
                payment_ledger = Ledger.objects.get(name='Cash in Hand (POS)')
            
            voucher = Voucher.objects.create(
                date=invoice.date,
                voucher_type='Receipt',
                narration=f"POS Invoice: {invoice.invoice_number} - {customer.name}",
                created_by=request.user,
                is_finalized=True
            )
            
            VoucherEntry.objects.create(voucher=voucher, ledger=payment_ledger, debit=invoice.grand_total)
            
            sales_ledger_totals = {}
            for line in invoice.items.all():
                ledger = line.item.sales_account if line.item.sales_account else ledger_sales
                sales_ledger_totals[ledger] = sales_ledger_totals.get(ledger, 0) + line.amount
                
                if line.item.item_type == 'Goods':
                    line.item.current_stock -= line.quantity
                    line.item.save()
            
            for s_ledger, amount in sales_ledger_totals.items():
                VoucherEntry.objects.create(voucher=voucher, ledger=s_ledger, credit=amount)
                
            if invoice.tax_amount > 0:
                VoucherEntry.objects.create(voucher=voucher, ledger=ledger_vat, credit=invoice.tax_amount)
            
            invoice.status = 'Finalized'
            invoice.save()
            
            return JsonResponse({
                'success': True, 
                'invoice_id': invoice.id,
                'invoice_number': invoice.invoice_number
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
