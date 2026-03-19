from django.core.management.base import BaseCommand
from accounting.models import Ledger, Voucher, VoucherEntry, AccountGroup
from inventory.models import Item, UnitOfMeasurement, StockAdjustment
from contacts.models import Contact
from sales.models import Invoice, InvoiceItem
from purchases.models import PurchaseInvoice, PurchaseInvoiceItem
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Seeds sample data into the current tenant schema'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data seeding...'))
        
        with transaction.atomic():
            # 1. Ledgers
            self.stdout.write('Ensuring core ledgers...')
            Ledger.ensure_core_ledgers()
            
            # 2. Units of Measurement
            self.stdout.write('Seeding Units of Measurement...')
            pcs, _ = UnitOfMeasurement.objects.get_or_create(name='Pieces', short_name='Pcs')
            kg, _ = UnitOfMeasurement.objects.get_or_create(name='Kilograms', short_name='Kg')
            box, _ = UnitOfMeasurement.objects.get_or_create(name='Box', short_name='Box')
            ltr, _ = UnitOfMeasurement.objects.get_or_create(name='Liters', short_name='Ltr')
            
            # 3. Items
            self.stdout.write('Seeding Inventory Items...')
            items_to_create = [
                {
                    'name': 'Dell XPS 15 Laptop',
                    'sku': 'LAP-DELL-XPS15',
                    'uom': pcs,
                    'sales_price': 185000.00,
                    'purchase_price': 160000.00,
                    'is_taxable': True,
                    'tax_rate': 13.00
                },
                {
                    'name': 'Logitech MX Master 3S',
                    'sku': 'ACC-LOGI-MX3S',
                    'uom': pcs,
                    'sales_price': 12500.00,
                    'purchase_price': 9500.00,
                    'is_taxable': True,
                    'tax_rate': 13.00
                },
                {
                    'name': 'A4 Paper Bundle (75 GSM)',
                    'sku': 'STA-A4-75GSM',
                    'uom': box,
                    'sales_price': 950.00,
                    'purchase_price': 750.00,
                    'is_taxable': False,
                    'tax_rate': 0.00
                },
                {
                    'name': 'Samsung 27" 4K Monitor',
                    'sku': 'MON-SAM-27-4K',
                    'uom': pcs,
                    'sales_price': 45000.00,
                    'purchase_price': 38000.00,
                    'is_taxable': True,
                    'tax_rate': 13.00
                }
            ]
            
            for item_data in items_to_create:
                Item.objects.get_or_create(sku=item_data['sku'], defaults=item_data)
                
            # 4. Contacts
            self.stdout.write('Seeding Contacts...')
            contacts_to_create = [
                {
                    'name': 'Himalayan Trading Pvt. Ltd.',
                    'contact_type': 'Customer',
                    'pan_vat_number': '301234567',
                    'phone': '01-4412345',
                    'email': 'info@himalayan.com.np',
                    'address': 'Durbarmarg, Kathmandu'
                },
                {
                    'name': 'Kathmandu Valley School',
                    'contact_type': 'Customer',
                    'pan_vat_number': '601234567',
                    'phone': '01-5512345',
                    'email': 'admin@kvs.edu.np',
                    'address': 'Lalitpur'
                },
                {
                    'name': 'Neoteric Nepal',
                    'contact_type': 'Supplier',
                    'pan_vat_number': '302234567',
                    'phone': '01-4423456',
                    'email': 'sales@neoteric.com.np',
                    'address': 'Jawalakhel'
                },
                {
                    'name': 'Ocean Computer',
                    'contact_type': 'Supplier',
                    'pan_vat_number': '303234567',
                    'phone': '01-4434567',
                    'email': 'orders@ocean.com.np',
                    'address': 'New Road, Kathmandu'
                }
            ]
            
            for contact_data in contacts_to_create:
                Contact.objects.get_or_create(pan_vat_number=contact_data['pan_vat_number'], defaults=contact_data)

            # Assign a user to transactions
            from users.models import CustomUser
            admin_user = CustomUser.objects.filter(is_superuser=True).first()

            # 5. Purchase Invoices (Finalized)
            self.stdout.write('Seeding Purchase Invoices...')
            supplier = Contact.objects.filter(contact_type='Supplier').first()
            if supplier:
                p_invoice, created = PurchaseInvoice.objects.get_or_create(
                    bill_number='BILL-2024-0001',
                    defaults={
                        'vendor': supplier,
                        'date': timezone.now().date() - timedelta(days=10),
                        'status': 'Finalized',
                        'sub_total': 160000.00,
                        'tax_amount': 20800.00,
                        'grand_total': 180800.00,
                        'notes': 'Demo purchase of stock',
                        'created_by': admin_user
                    }
                )
                if created:
                    PurchaseInvoiceItem.objects.create(
                        purchase_invoice=p_invoice,
                        item=Item.objects.get(sku='LAP-DELL-XPS15'),
                        quantity=1,
                        unit_price=160000.00,
                        amount=160000.00,
                        tax_amount=20800.00
                    )
                    # Accounting for Purchase
                    ledger_purchase = Ledger.objects.get(name='Local Purchase')
                    ledger_p_vat = Ledger.objects.get(name='Purchase VAT (13%)')
                    ledger_payable = Ledger.objects.get(name='Accounts Payable (General)')
                    
                    p_voucher = Voucher.objects.create(
                        date=p_invoice.date,
                        voucher_type='Purchase',
                        narration=f"Demo Purchase Bill: {p_invoice.bill_number}",
                        is_finalized=True,
                        created_by=admin_user
                    )
                    VoucherEntry.objects.create(voucher=p_voucher, ledger=ledger_purchase, debit=160000.00)
                    VoucherEntry.objects.create(voucher=p_voucher, ledger=ledger_p_vat, debit=20800.00)
                    VoucherEntry.objects.create(voucher=p_voucher, ledger=ledger_payable, credit=180800.00)

            # 6. Sales Invoices (Draft & Finalized)
            self.stdout.write('Seeding Sales Invoices...')
            customer = Contact.objects.filter(contact_type='Customer').first()
            if customer:
                # One Finalized
                s_invoice, created = Invoice.objects.get_or_create(
                    invoice_number='INV-2024-0001',
                    defaults={
                        'customer': customer,
                        'date': timezone.now().date() - timedelta(days=5),
                        'status': 'Finalized',
                        'sub_total': 12500.00,
                        'tax_amount': 1625.00,
                        'grand_total': 14125.00,
                        'notes': 'Demo finalized sale',
                        'created_by': admin_user
                    }
                )
                if created:
                    InvoiceItem.objects.create(
                        invoice=s_invoice,
                        item=Item.objects.get(sku='ACC-LOGI-MX3S'),
                        quantity=1,
                        unit_price=12500.00,
                        amount=12500.00,
                        tax_amount=1625.00
                    )
                    # Accounting for Sale
                    ledger_sales = Ledger.objects.get(name='Local Sales')
                    ledger_s_vat = Ledger.objects.get(name='Sales VAT (13%)')
                    ledger_receivable = Ledger.objects.get(name='Accounts Receivable (General)')
                    
                    s_voucher = Voucher.objects.create(
                        date=s_invoice.date,
                        voucher_type='Sales',
                        narration=f"Demo Sale Invoice: {s_invoice.invoice_number}",
                        is_finalized=True,
                        created_by=admin_user
                    )
                    VoucherEntry.objects.create(voucher=s_voucher, ledger=ledger_receivable, debit=14125.00)
                    VoucherEntry.objects.create(voucher=s_voucher, ledger=ledger_sales, credit=12500.00)
                    VoucherEntry.objects.create(voucher=s_voucher, ledger=ledger_s_vat, credit=1625.00)

                # One Draft
                Invoice.objects.get_or_create(
                    invoice_number='INV-2024-0002',
                    defaults={
                        'customer': customer,
                        'date': timezone.now().date(),
                        'status': 'Draft',
                        'sub_total': 0,
                        'tax_amount': 0,
                        'grand_total': 0,
                        'notes': 'Draft invoice for followup'
                    }
                )

            # 7. Manual Vouchers (Payment/Receipt)
            self.stdout.write('Seeding Manual Vouchers...')
            cash_ledger = Ledger.objects.get(name='Cash in Hand')
            receivable_ledger = Ledger.objects.get(name='Accounts Receivable (General)')
            operating_group = AccountGroup.objects.get(name='Operating Expenses')
            rent_ledger, _ = Ledger.objects.get_or_create(name='Office Rent', defaults={'group': operating_group, 'account_type': 'Expense'})
            
            # Payment for Rent
            pay_voucher = Voucher.objects.create(
                date=timezone.now().date() - timedelta(days=2),
                voucher_type='Payment',
                narration='Monthly Office Rent Payment',
                is_finalized=True,
                created_by=admin_user
            )
            VoucherEntry.objects.create(voucher=pay_voucher, ledger=rent_ledger, debit=25000.00)
            VoucherEntry.objects.create(voucher=pay_voucher, ledger=cash_ledger, credit=25000.00)

            # Receipt from Customer
            rec_voucher = Voucher.objects.create(
                date=timezone.now().date() - timedelta(days=1),
                voucher_type='Receipt',
                narration='Partial collection from Himalayan Trading',
                is_finalized=True,
                created_by=admin_user
            )
            VoucherEntry.objects.create(voucher=rec_voucher, ledger=cash_ledger, debit=10000.00)
            VoucherEntry.objects.create(voucher=rec_voucher, ledger=receivable_ledger, credit=10000.00)

            # 8. Stock Adjustments
            self.stdout.write('Seeding Stock Adjustments...')
            monitor = Item.objects.get(sku='MON-SAM-27-4K')
            laptop = Item.objects.get(sku='LAP-DELL-XPS15')
            
            # Initial stock count (Addition)
            StockAdjustment.objects.create(
                item=monitor,
                quantity=10,
                adjustment_type='Addition',
                reason='Initial warehouse count',
                performed_by=admin_user
            )
            monitor.current_stock += 10
            monitor.save()

            # Damage (Reduction)
            StockAdjustment.objects.create(
                item=monitor,
                quantity=1,
                adjustment_type='Breakage',
                reason='Damaged during transit',
                performed_by=admin_user
            )
            monitor.current_stock -= 1
            monitor.save()

            # Initial stock for laptop
            StockAdjustment.objects.create(
                item=laptop,
                quantity=5,
                adjustment_type='Addition',
                reason='Stock transfer from main branch',
                performed_by=admin_user
            )
            laptop.current_stock += 5
            laptop.save()
                
        self.stdout.write(self.style.SUCCESS('Sample data seeded successfully!'))
