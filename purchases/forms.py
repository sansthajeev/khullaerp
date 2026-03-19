from django import forms
from django.forms import inlineformset_factory
from .models import PurchaseInvoice, PurchaseInvoiceItem

class PurchaseInvoiceForm(forms.ModelForm):
    class Meta:
        model = PurchaseInvoice
        fields = ['vendor', 'vendor_invoice_number', 'date', 'due_date', 'notes', 'status', 'tds_heading', 'tds_account']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'text', 'class': 'form-control', 'id': 'nepali-datepicker-ad'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'vendor_invoice_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional Vendor Ref'}),
            'vendor': forms.Select(attrs={'class': 'form-select', 'id': 'vendor-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'tds_heading': forms.Select(attrs={'class': 'form-select'}),
            'tds_account': forms.Select(attrs={'class': 'form-select'}),
        }

class PurchaseInvoiceItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseInvoiceItem
        fields = ['item', 'description', 'quantity', 'unit_price', 'tax_rate', 'tds_rate']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional description'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tds_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'x-model.number': 'tds_rate', 'placeholder': '%'}),
        }

PurchaseInvoiceItemFormSet = inlineformset_factory(
    PurchaseInvoice, PurchaseInvoiceItem,
    form=PurchaseInvoiceItemForm,
    extra=1,
    can_delete=True
)
