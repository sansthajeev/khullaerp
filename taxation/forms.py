from django import forms
from django.forms import inlineformset_factory
from .models import TDSJournal, TDSJournalLine, TDSHeading
from accounting.models import Ledger
from hr.models import Employee
from contacts.models import Contact

class TDSHeadingForm(forms.ModelForm):
    class Meta:
        model = TDSHeading
        fields = ['code', 'name', 'description']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 11112'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Salary Tax'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Optional description...', 'rows': 3}),
        }

class TDSJournalForm(forms.ModelForm):
    # Field to select document numbering or other header info if needed
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    narration = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=False)

    class Meta:
        model = TDSJournal
        fields = [] # Journal header mostly comes from the linked Voucher

class TDSJournalLineForm(forms.ModelForm):
    class Meta:
        model = TDSJournalLine
        fields = [
            'ledger', 'subledger_type', 'employee', 'contact', 
            'debit', 'credit', 'tds_heading', 'taxable_ledger', 
            'payment_amount', 'remarks'
        ]
        widgets = {
            'ledger': forms.Select(attrs={'class': 'form-select ledger-select'}),
            'subledger_type': forms.Select(attrs={'class': 'form-select'}),
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'contact': forms.Select(attrs={'class': 'form-select'}),
            'debit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'credit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tds_heading': forms.Select(attrs={'class': 'form-select'}),
            'taxable_ledger': forms.Select(attrs={'class': 'form-select'}),
            'payment_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'remarks': forms.TextInput(attrs={'class': 'form-control'}),
        }

TDSJournalLineFormSet = inlineformset_factory(
    TDSJournal, TDSJournalLine, form=TDSJournalLineForm,
    extra=1, can_delete=True
)
