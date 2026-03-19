from django import forms
from .models import Item, StockAdjustment, UnitOfMeasurement

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'sku', 'barcode', 'item_type', 'uom', 'valuation_method', 'sales_price', 'purchase_price', 'is_taxable', 'tax_rate', 'sales_account', 'purchase_account', 'cogs_account']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Consulting Services / Basmati Rice'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CS-001 / BR-10KG'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional: Scan or type custom barcode'}),
            'item_type': forms.Select(attrs={'class': 'form-select border-0 bg-light fw-bold text-primary', '@change': 'type = $event.target.value'}),
            'uom': forms.Select(attrs={'class': 'form-select border-0 bg-light'}),
            'valuation_method': forms.Select(attrs={'class': 'form-select border-0 bg-light'}),
            'sales_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '13.00', 'step': '0.01'}),
            'sales_account': forms.Select(attrs={'class': 'form-select'}),
            'purchase_account': forms.Select(attrs={'class': 'form-select'}),
            'cogs_account': forms.Select(attrs={'class': 'form-select'}),
        }

class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockAdjustment
        fields = ['item', 'adjustment_type', 'quantity', 'reason']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select border-0 bg-light'}),
            'adjustment_type': forms.Select(attrs={'class': 'form-select border-0 bg-light'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.000', 'step': '0.001'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Why are you adjusting the stock?'}),
        }
