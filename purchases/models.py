from django.db import models
from django.conf import settings
from contacts.models import Contact
from inventory.models import Item
from django.utils import timezone

class PurchaseInvoice(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Finalized', 'Finalized'),
        ('Cancelled', 'Cancelled'),
    ]
    
    bill_number = models.CharField(max_length=50, unique=True, editable=False)
    vendor_invoice_number = models.CharField(max_length=50, blank=True, help_text="The invoice number from the supplier")
    vendor = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='purchase_invoices', limit_choices_to={'contact_type__in': ['Supplier', 'Both']})
    date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    
    # Financial Totals
    sub_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    tds_heading = models.ForeignKey('taxation.TDSHeading', on_delete=models.SET_NULL, null=True, blank=True)
    tds_account = models.ForeignKey('accounting.Ledger', on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'name__icontains': 'TDS'}, related_name='+')

    def save(self, *args, **kwargs):
        if not self.bill_number:
            year = timezone.now().year
            last_bill = PurchaseInvoice.objects.filter(bill_number__contains=f'BILL-{year}-').order_by('id').last()
            if not last_bill:
                self.bill_number = f'BILL-{year}-0001'
            else:
                last_id_str = last_bill.bill_number.split('-')[-1]
                try:
                    new_id = int(last_id_str) + 1
                except ValueError:
                    new_id = 1
                self.bill_number = f'BILL-{year}-{str(new_id).zfill(4)}'
        
        # Calculate Grand Total (Before TDS)
        self.grand_total = self.sub_total + self.tax_amount - self.discount_amount
        super().save(*args, **kwargs)

    @property
    def total_tds(self):
        return sum(item.tds_amount for item in self.items.all())

    @property
    def net_payable(self):
        return self.grand_total - self.total_tds

    def __str__(self):
        return self.bill_number

class PurchaseInvoiceItem(models.Model):
    purchase_invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    
    amount = models.DecimalField(max_digits=15, decimal_places=2, editable=False)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=13.00)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, editable=False)
    
    tds_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True, null=True)
    tds_amount = models.DecimalField(max_digits=15, decimal_places=2, editable=False, default=0)
    
    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.unit_price
        self.tax_amount = (self.amount * self.tax_rate) / 100
        tds_pct = self.tds_rate if self.tds_rate else 0
        self.tds_amount = (self.amount * tds_pct) / 100
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.purchase_invoice.bill_number} - {self.item.name}"
