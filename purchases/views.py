from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import PurchaseInvoice, PurchaseInvoiceItem
from .forms import PurchaseInvoiceForm, PurchaseInvoiceItemFormSet
from accounting.models import Voucher, VoucherEntry, Ledger
from inventory.models import Item
from taxation.models import TDSJournal, TDSJournalLine
import json

@login_required
def purchase_list(request):
    purchases = PurchaseInvoice.objects.all().order_by('-date', '-created_at')
    return render(request, 'purchases/purchase_list.html', {'purchases': purchases})

@login_required
def purchase_create(request):
    if request.method == 'POST':
        form = PurchaseInvoiceForm(request.POST)
        formset = PurchaseInvoiceItemFormSet(request.POST, prefix='items')
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                purchase = form.save(commit=False)
                purchase.created_by = request.user
                purchase.save()
                
                formset.instance = purchase
                formset.save()
                
                # Recalculate totals
                sub_total = 0
                tax_total = 0
                for item in purchase.items.all():
                    sub_total += item.amount
                    tax_total += item.tax_amount
                
                purchase.sub_total = sub_total
                purchase.tax_amount = tax_total
                purchase.grand_total = sub_total + tax_total - purchase.discount_amount
                purchase.save()
                
                if purchase.grand_total <= 0:
                    transaction.set_rollback(True)
                    messages.error(request, "Purchase Bill total must be greater than zero.")
                else:
                    messages.success(request, f"Purchase Bill {purchase.bill_number} created.")
                    return redirect('purchases:purchase_detail', pk=purchase.pk)
    else:
        form = PurchaseInvoiceForm()
        formset = PurchaseInvoiceItemFormSet(prefix='items')
        
    items_data = {
        item.id: {
            'price': float(item.purchase_price),
            'tax': float(item.tax_rate) if item.is_taxable else 0
        } for item in Item.objects.all()
    }
    
    return render(request, 'purchases/purchase_create.html', {
        'form': form,
        'formset': formset,
        'items_data_json': json.dumps(items_data),
        'default_vat_rate': float(request.tenant.default_vat_rate) if request.tenant.is_vat_registered else 0
    })

@login_required
def purchase_detail(request, pk):
    purchase = get_object_or_404(PurchaseInvoice, pk=pk)
    return render(request, 'purchases/purchase_detail.html', {'purchase': purchase})

@login_required
def finalize_purchase(request, pk):
    purchase = get_object_or_404(PurchaseInvoice, pk=pk)
    
    if purchase.status != 'Draft':
        messages.error(request, "Only draft bills can be finalized.")
        return redirect('purchases:purchase_detail', pk=purchase.pk)
    
    if request.method == 'POST':
        with transaction.atomic():
            # 1. Ensure Ledgers
            Ledger.ensure_core_ledgers()
            ledger_purchase = Ledger.objects.get(name='Local Purchase')
            ledger_vat = Ledger.objects.get(name='Purchase VAT (13%)')
            ledger_payable = Ledger.objects.get(name='Accounts Payable (General)')
            
            # 2. Create Voucher
            voucher = Voucher.objects.create(
                date=purchase.date,
                voucher_type='Purchase',
                narration=f"Purchase Bill: {purchase.bill_number} from {purchase.vendor.name}",
                created_by=request.user,
                is_finalized=True
            )
            
            # 3. Double Entry
            # Group purchase amounts by specific Item Ledgers or Default Purchase Ledger
            purchase_ledger_totals = {}
            for line in purchase.items.all():
                ledger = line.item.purchase_account if line.item.purchase_account else ledger_purchase
                if ledger not in purchase_ledger_totals:
                    purchase_ledger_totals[ledger] = 0
                purchase_ledger_totals[ledger] += line.amount
            
            # Debit targeted Purchase/Expense ledgers
            for ledger, amount in purchase_ledger_totals.items():
                if amount > 0:
                    VoucherEntry.objects.create(
                        voucher=voucher,
                        ledger=ledger,
                        debit=amount
                    )
            
            # Debit Purchase VAT (Tax)
            if purchase.tax_amount > 0:
                VoucherEntry.objects.create(
                    voucher=voucher,
                    ledger=ledger_vat,
                    debit=purchase.tax_amount
                )
            
            # Credit TDS Payable (TDS Amount evaluated dynamically on items)
            tds_lines = []
            for line in purchase.items.all():
                if line.tds_amount > 0:
                    tds_lines.append(line)
                    
            if tds_lines:
                tds_journal = TDSJournal.objects.create(voucher=voucher)
                
                for line in tds_lines:
                    ledger = purchase.tds_account if purchase.tds_account else Ledger.objects.get(name='TDS Payable')
                    
                    # 1. Base Accounting Entry
                    VoucherEntry.objects.create(
                        voucher=voucher,
                        ledger=ledger,
                        credit=line.tds_amount
                    )
                    
                    # 2. TDS Register Entry
                    TDSJournalLine.objects.create(
                        tds_journal=tds_journal,
                        ledger=ledger, # The Liability Account
                        taxable_ledger=line.item.purchase_account if line.item.purchase_account else ledger_purchase,
                        subledger_type='Contact',
                        contact=purchase.vendor,
                        credit=line.tds_amount,
                        tds_heading=purchase.tds_heading,
                        payment_amount=line.amount,
                        remarks=f"Purchase Bill {purchase.bill_number}"
                    )
                
            # Compute real Grand Total dynamically for payable split
            total_tds = sum([line.tds_amount for line in tds_lines])
            total_payable = purchase.grand_total - total_tds
                
            # Credit Accounts Payable (Total)
            VoucherEntry.objects.create(
                voucher=voucher,
                ledger=ledger_payable,
                credit=total_payable
            )
            
            # 4. Integrate Stock (Add purchased quantities for Goods)
            for line in purchase.items.all():
                item = line.item
                if item.item_type == 'Goods':
                    item.current_stock += line.quantity
                    item.save()
            
            # 5. Finalize
            purchase.status = 'Finalized'
            purchase.save()
            
            messages.success(request, f"Purchase Bill {purchase.bill_number} finalized. Stock and accounting updated.")
            
    return redirect('purchases:purchase_detail', pk=purchase.pk)
@login_required
def purchase_delete(request, pk):
    purchase = get_object_or_404(PurchaseInvoice, pk=pk)
    if request.method == 'POST':
        with transaction.atomic():
            # Also find and delete the linked voucher if it exists
            Voucher.objects.filter(narration__contains=f"Purchase Bill: {purchase.bill_number}").delete()
            purchase.delete()
            messages.success(request, f"Purchase Bill {purchase.bill_number} and associated accounting records deleted.")
        return redirect('purchases:purchase_list')
    return render(request, 'purchases/purchase_confirm_delete.html', {'purchase': purchase})
