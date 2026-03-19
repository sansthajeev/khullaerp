from django.db import models
from django.conf import settings
from accounting.models import Ledger
import barcode
from barcode.writer import ImageWriter
import qrcode
import qrcode.image.svg
from io import BytesIO
import base64

class UnitOfMeasurement(models.Model):
    name = models.CharField(max_length=50) # kg, pieces, bundles
    short_name = models.CharField(max_length=10)
    
    def __str__(self):
        return self.name

class Item(models.Model):
    VALUATION_METHODS = [
        ('FIFO', 'FIFO'),
        ('Weighted Average', 'Weighted Average'),
    ]
    ITEM_TYPES = [
        ('Goods', 'Goods / Physical Product'),
        ('Service', 'Service'),
    ]
    
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True)
    barcode = models.CharField(max_length=100, blank=True, null=True, help_text="Specific Barcode (EAN, UPC, etc.) - Falls back to SKU if empty")
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, default='Goods')
    uom = models.ForeignKey(UnitOfMeasurement, on_delete=models.CASCADE)
    valuation_method = models.CharField(max_length=20, choices=VALUATION_METHODS, default='FIFO')
    sales_price = models.DecimalField(max_digits=12, decimal_places=2)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2)
    current_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    
    # Tax categories
    is_taxable = models.BooleanField(default=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=13.00) # Default 13% VAT
    
    # Financial Ledgers Overrides
    sales_account = models.ForeignKey(Ledger, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_items', limit_choices_to={'account_type': 'Income'})
    purchase_account = models.ForeignKey(Ledger, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_items', limit_choices_to={'account_type': 'Expense'})
    cogs_account = models.ForeignKey(Ledger, on_delete=models.SET_NULL, null=True, blank=True, related_name='cogs_items', limit_choices_to={'account_type': 'Expense'})
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.barcode:
            # Generate a 12-digit random numeric string for barcode if empty
            import random
            import string
            # Start with 20 (internal use) followed by 10 random digits
            self.barcode = '20' + ''.join(random.choices(string.digits, k=10))
        super().save(*args, **kwargs)

    def generate_barcode(self):
        """Generates a barcode image for the Barcode/SKU and returns it as a base64 string."""
        value = self.barcode if self.barcode else self.sku
        EAN = barcode.get_barcode_class('code128')
        ean = EAN(value, writer=ImageWriter())
        buffer = BytesIO()
        ean.write(buffer)
        return base64.b64encode(buffer.getvalue()).decode()

    def generate_qr_code(self):
        """Generates a QR code for the Barcode/SKU and returns it as an SVG string."""
        value = self.barcode if self.barcode else self.sku
        factory = qrcode.image.svg.SvgImage
        img = qrcode.make(value, image_factory=factory, box_size=10)
        buffer = BytesIO()
        img.save(buffer)
        return buffer.getvalue().decode()

class StockAdjustment(models.Model):
    ADJUSTMENT_TYPES = [
        ('Addition', 'Addition'),
        ('Reduction', 'Reduction'),
        ('Breakage', 'Breakage'),
    ]
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPES)
    reason = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"{self.adjustment_type} - {self.item.name}"
