from django import forms
from django.db import models
from django.forms import inlineformset_factory
from .models import Voucher, VoucherEntry, Ledger

class VoucherForm(forms.ModelForm):
    cash_bank_ledger = forms.ModelChoiceField(
        queryset=Ledger.objects.all(),
        required=False,
        label="Cash/Bank Account",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'header_ledger_select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter liquidity ledgers for the header field reliably
        self.fields['cash_bank_ledger'].queryset = Ledger.objects.filter(
            account_type='Asset'
        ).filter(
            models.Q(name__icontains='Cash') |
            models.Q(name__icontains='Bank') |
            models.Q(group__name__icontains='Bank') |
            models.Q(group__name__icontains='Cash')
        )

    class Meta:
        model = Voucher
        fields = ['date', 'voucher_type', 'narration']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'ad_date'}),
            'voucher_type': forms.Select(attrs={'class': 'form-control', '@change': 'vType = $event.target.value'}),
            'narration': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class VoucherEntryForm(forms.ModelForm):
    class Meta:
        model = VoucherEntry
        fields = ['ledger', 'contact', 'employee', 'debit', 'credit']
        widgets = {
            'ledger': forms.Select(attrs={'class': 'form-control', '@change': 'checkSubledger($event)'}),
            'contact': forms.Select(attrs={'class': 'form-control', 'x-show': 'showSubledger'}),
            'employee': forms.Select(attrs={'class': 'form-control', 'x-show': 'showEmployeeSubledger'}),
            'debit': forms.NumberInput(attrs={'step': 'any', 'class': 'form-control debit-input', 'min': '0'}),
            'credit': forms.NumberInput(attrs={'step': 'any', 'class': 'form-control credit-input', 'min': '0'}),
        }

VoucherEntryFormSet = inlineformset_factory(
    Voucher, VoucherEntry, form=VoucherEntryForm,
    extra=1, can_delete=True
)
