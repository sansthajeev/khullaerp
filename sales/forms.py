from django import forms
from django.forms import inlineformset_factory
from .models import Invoice, InvoiceItem

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['customer', 'date', 'due_date', 'notes', 'discount_type', 'discount_value', 'discount_amount']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'discount_type': forms.HiddenInput(),
            'discount_value': forms.HiddenInput(),
            'discount_amount': forms.HiddenInput(),
        }

class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['item', 'description', 'quantity', 'unit_price', 'tax_rate']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select item-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional description'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control qty-input', 'step': '0.001'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control rate-input', 'step': '0.01'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control tax-input', 'step': '0.01'}),
        }

InvoiceItemFormSet = inlineformset_factory(
    Invoice, InvoiceItem, form=InvoiceItemForm,
    extra=1, can_delete=True
)
