from django.db import models
from django.conf import settings
from contacts.models import Contact
from inventory.models import Item
from django.utils import timezone

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Finalized', 'Finalized'),
        ('Cancelled', 'Cancelled'),
    ]
    
    invoice_number = models.CharField(max_length=50, unique=True, editable=False)
    customer = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='invoices')
    date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    
    # Financial Totals
    sub_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount_type = models.CharField(max_length=10, choices=[('fixed', 'Fixed'), ('percent', 'Percent')], default='fixed')
    discount_value = models.DecimalField(max_digits=15, decimal_places=2, default=0) # Value entered (e.g., 10 for 10%)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0) # Calculated flat amount
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0) # Total VAT
    grand_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate format: INV-2024-0001
            year = timezone.now().year
            last_invoice = Invoice.objects.filter(invoice_number__contains=f'INV-{year}-').order_by('id').last()
            if not last_invoice:
                self.invoice_number = f'INV-{year}-0001'
            else:
                last_id_str = last_invoice.invoice_number.split('-')[-1]
                new_id = int(last_id_str) + 1
                self.invoice_number = f'INV-{year}-{str(new_id).zfill(4)}'
        
        if self.discount_type == 'percent':
            self.discount_amount = (self.sub_total * self.discount_value) / 100
        else:
            self.discount_amount = self.discount_value
            
        # Calculate Grand Total
        self.grand_total = self.sub_total + self.tax_amount - self.discount_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    description = models.TextField(blank=True) # Optional line-specific description
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Totals for this line
    amount = models.DecimalField(max_digits=15, decimal_places=2, editable=False)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=13.00)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, editable=False)
    
    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.unit_price
        self.tax_amount = (self.amount * self.tax_rate) / 100
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.item.name}"
