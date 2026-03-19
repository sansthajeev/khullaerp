from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, models
from django.apps import apps
from .models import Item, UnitOfMeasurement, StockAdjustment
from .forms import ItemForm, StockAdjustmentForm

@login_required
def item_list(request):
    items = Item.objects.all().order_by('name')
    return render(request, 'inventory/item_list.html', {'items': items})

@login_required
def item_bulk_generate_barcodes(request):
    """Generates barcodes for all items that don't have one."""
    items_without_barcode = Item.objects.filter(models.Q(barcode__isnull=True) | models.Q(barcode=''))
    count = items_without_barcode.count()
    
    if count > 0:
        for item in items_without_barcode:
            # item.save() will trigger the auto-generation logic we added earlier
            item.save()
        messages.success(request, f"Successfully generated barcodes for {count} items.")
    else:
        messages.info(request, "All items already have barcodes.")
        
    return redirect('inventory:item_list')

@login_required
def item_detail(request, pk):
    item = get_object_or_404(Item, pk=pk)
    barcode_base64 = item.generate_barcode()
    qr_code_svg = item.generate_qr_code()
    return render(request, 'inventory/item_detail.html', {
        'item': item,
        'barcode': barcode_base64,
        'qr_code': qr_code_svg
    })

@login_required
def item_create(request):
    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"Item '{item.name}' created successfully.")
            return redirect('inventory:item_list')
    else:
        form = ItemForm()
    
    uoms = UnitOfMeasurement.objects.all()
    return render(request, 'inventory/item_create.html', {
        'form': form,
        'uoms': uoms,
        'is_edit': False
    })

@login_required
def item_edit(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method == 'POST':
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"Item '{item.name}' updated successfully.")
            return redirect('inventory:item_list')
    else:
        form = ItemForm(instance=item)
    
    uoms = UnitOfMeasurement.objects.all()
    return render(request, 'inventory/item_create.html', {
        'form': form,
        'item': item,
        'uoms': uoms,
        'is_edit': True
    })

@login_required
def item_delete(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method == 'POST':
        item_name = item.name
        item.delete()
        messages.success(request, f"Item '{item_name}' deleted successfully.")
        return redirect('inventory:item_list')
    return render(request, 'inventory/item_confirm_delete.html', {'item': item})

# --- Stock Adjustments ---

@login_required
def adjustment_list(request):
    adjustments = StockAdjustment.objects.all().order_by('-date')
    return render(request, 'inventory/adjustment_list.html', {'adjustments': adjustments})

@login_required
def adjustment_create(request):
    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                adjustment = form.save(commit=False)
                adjustment.performed_by = request.user
                adjustment.save()
                
                # Update Item stock
                item = adjustment.item
                if adjustment.adjustment_type == 'Addition':
                    item.current_stock += adjustment.quantity
                else: # Reduction or Breakage
                    item.current_stock -= adjustment.quantity
                item.save()
                
                messages.success(request, f"Stock adjusted for {item.name}.")
                return redirect('inventory:adjustment_list')
    else:
        # Pre-select item if provided in GET
        item_id = request.GET.get('item')
        form = StockAdjustmentForm(initial={'item': item_id}) if item_id else StockAdjustmentForm()
        
    return render(request, 'inventory/adjustment_form.html', {'form': form})

@login_required
def adjustment_delete(request, pk):
    adjustment = get_object_or_404(StockAdjustment, pk=pk)
    if request.method == 'POST':
        with transaction.atomic():
            # Reverse stock impact before deleting
            item = adjustment.item
            if adjustment.adjustment_type == 'Addition':
                item.current_stock -= adjustment.quantity
            else:
                item.current_stock += adjustment.quantity
            item.save()
            
            adjustment.delete()
            messages.success(request, "Stock adjustment reversed and deleted.")
        return redirect('inventory:adjustment_list')
    return render(request, 'inventory/adjustment_confirm_delete.html', {'adjustment': adjustment})
from django.db.models import Sum, Q
from accounting.views import get_report_dates # Reuse the established date parser

@login_required
def stock_report(request):
    from_date, to_date = get_report_dates(request)
    items = Item.objects.all().order_by('name')
    
    report_data = []
    total_inventory_value = 0
    
    for item in items:
        # --- Opening Balance Calculation ---
        # Value at current purchase price as a simplified cost basis for opening
        purch_prior = apps.get_model('purchases', 'PurchaseInvoiceItem').objects.filter(
            item=item, purchase_invoice__date__lt=from_date, purchase_invoice__status='Finalized'
        ).aggregate(qty=Sum('quantity'))['qty'] or 0
        
        adj_in_prior = StockAdjustment.objects.filter(
            item=item, date__date__lt=from_date, adjustment_type='Addition'
        ).aggregate(qty=Sum('quantity'))['qty'] or 0
        
        sales_prior = apps.get_model('sales', 'InvoiceItem').objects.filter(
            item=item, invoice__date__lt=from_date, invoice__status='Finalized'
        ).aggregate(qty=Sum('quantity'))['qty'] or 0
        
        adj_out_prior = StockAdjustment.objects.filter(
            item=item, date__date__lt=from_date, adjustment_type__in=['Reduction', 'Breakage']
        ).aggregate(qty=Sum('quantity'))['qty'] or 0
        
        opening_qty = purch_prior + adj_in_prior - sales_prior - adj_out_prior
        opening_amt = opening_qty * item.purchase_price
        
        # --- Inward Movements in Range ---
        # Includes aggregate purchase amount and adjustments
        purch_res = apps.get_model('purchases', 'PurchaseInvoiceItem').objects.filter(
            item=item, purchase_invoice__date__range=(from_date, to_date), purchase_invoice__status='Finalized'
        ).aggregate(qty=Sum('quantity'), amt=Sum('amount'))
        
        inward_purch_qty = purch_res['qty'] or 0
        inward_purch_amt = purch_res['amt'] or 0
        
        inward_adj_qty = StockAdjustment.objects.filter(
            item=item, date__date__range=(from_date, to_date), adjustment_type='Addition'
        ).aggregate(qty=Sum('quantity'))['qty'] or 0
        inward_adj_amt = inward_adj_qty * item.purchase_price
        
        inward_qty = inward_purch_qty + inward_adj_qty
        inward_amt = inward_purch_amt + inward_adj_amt
        inward_cost = inward_amt / inward_qty if inward_qty > 0 else item.purchase_price
        
        # --- Outward Movements in Range ---
        # Valued at cost (purchase price) for stock valuation consistency
        outward_sales_qty = apps.get_model('sales', 'InvoiceItem').objects.filter(
            item=item, invoice__date__range=(from_date, to_date), invoice__status='Finalized'
        ).aggregate(qty=Sum('quantity'))['qty'] or 0
        
        outward_adj_qty = StockAdjustment.objects.filter(
            item=item, date__date__range=(from_date, to_date), adjustment_type__in=['Reduction', 'Breakage']
        ).aggregate(qty=Sum('quantity'))['qty'] or 0
        
        outward_qty = outward_sales_qty + outward_adj_qty
        outward_amt = outward_qty * item.purchase_price
        
        # --- Closing Balance ---
        closing_qty = opening_qty + inward_qty - outward_qty
        closing_amt = closing_qty * item.purchase_price
        total_inventory_value += closing_amt
        
        if opening_qty != 0 or inward_qty != 0 or outward_qty != 0:
            report_data.append({
                'item': item,
                'opening_qty': opening_qty,
                'opening_cost': item.purchase_price,
                'opening_amt': opening_amt,
                'inward_qty': inward_qty,
                'inward_cost': inward_cost,
                'inward_amt': inward_amt,
                'outward_qty': outward_qty,
                'outward_cost': item.purchase_price,
                'outward_amt': outward_amt,
                'closing_qty': closing_qty,
                'closing_cost': item.purchase_price,
                'closing_amt': closing_amt,
            })
            
    return render(request, 'inventory/reports/stock_report.html', {
        'report_data': report_data,
        'from_date': from_date,
        'to_date': to_date,
        'total_value': total_inventory_value
    })

@login_required
def stock_ledger(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    from_date, to_date = get_report_dates(request)

    # 1. Calculate Opening Balance before from_date
    purch_prior = apps.get_model('purchases', 'PurchaseInvoiceItem').objects.filter(
        item=item, purchase_invoice__date__lt=from_date, purchase_invoice__status='Finalized'
    ).aggregate(qty=Sum('quantity'))['qty'] or 0
    adj_in_prior = StockAdjustment.objects.filter(
        item=item, date__date__lt=from_date, adjustment_type='Addition'
    ).aggregate(qty=Sum('quantity'))['qty'] or 0
    sales_prior = apps.get_model('sales', 'InvoiceItem').objects.filter(
        item=item, invoice__date__lt=from_date, invoice__status='Finalized'
    ).aggregate(qty=Sum('quantity'))['qty'] or 0
    adj_out_prior = StockAdjustment.objects.filter(
        item=item, date__date__lt=from_date, adjustment_type__in=['Reduction', 'Breakage']
    ).aggregate(qty=Sum('quantity'))['qty'] or 0

    opening_qty = (purch_prior + adj_in_prior) - (sales_prior + adj_out_prior)
    opening_value = opening_qty * item.purchase_price

    # 2. Fetch Movements within date range
    movements = []

    # Purchases
    purchases = apps.get_model('purchases', 'PurchaseInvoiceItem').objects.filter(
        item=item, purchase_invoice__date__range=(from_date, to_date), purchase_invoice__status='Finalized'
    ).select_related('purchase_invoice', 'purchase_invoice__vendor')
    for p in purchases:
        movements.append({
            'date': p.purchase_invoice.date,
            'ref': f"Purchase {p.purchase_invoice.bill_number}",
            'source': p.purchase_invoice.vendor.name if getattr(p.purchase_invoice, 'vendor', None) else "Vendor",
            'type': 'inward',
            'qty': p.quantity,
            'rate': p.unit_price,
            'amount': p.amount,
            'obj': p
        })

    # Sales
    sales = apps.get_model('sales', 'InvoiceItem').objects.filter(
        item=item, invoice__date__range=(from_date, to_date), invoice__status='Finalized'
    ).select_related('invoice', 'invoice__customer')
    for s in sales:
        movements.append({
            'date': s.invoice.date,
            'ref': f"Sales {s.invoice.invoice_number}",
            'source': s.invoice.customer.name,
            'type': 'outward',
            'qty': s.quantity,
            'rate': s.unit_price,
            'amount': s.amount,
            'obj': s
        })

    # Adjustments
    adjustments = StockAdjustment.objects.filter(
        item=item, date__date__range=(from_date, to_date)
    )
    for a in adjustments:
        is_inward = a.adjustment_type == 'Addition'
        movements.append({
            'date': a.date.date(),
            'ref': f"Adjustment",
            'source': a.reason,
            'type': 'inward' if is_inward else 'outward',
            'qty': a.quantity,
            'rate': item.purchase_price,
            'amount': a.quantity * item.purchase_price,
            'obj': a
        })

    # 3. Sort chronologically
    movements.sort(key=lambda x: x['date'])

    # 4. Calculate Running Balances
    running_qty = opening_qty
    for m in movements:
        if m['type'] == 'inward':
            running_qty += m['qty']
        else:
            running_qty -= m['qty']
        m['running_qty'] = running_qty
        m['running_value'] = running_qty * item.purchase_price

    return render(request, 'inventory/stock_ledger.html', {
        'item': item,
        'from_date': from_date,
        'to_date': to_date,
        'opening_qty': opening_qty,
        'opening_value': opening_value,
        'movements': movements,
        'closing_qty': running_qty,
        'closing_value': running_qty * item.purchase_price
    })
