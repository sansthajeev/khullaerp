from django import forms
from .models import TenantRequest, Client

class ClientForm(forms.ModelForm):
    domain_name = forms.CharField(max_length=100, help_text="e.g. company-name (without .localhost)")
    
    class Meta:
        model = Client
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name'}),
        }

class TenantRequestForm(forms.ModelForm):
    class Meta:
        model = TenantRequest
        fields = ['company_name', 'subdomain', 'pan_number', 'contact_email', 'contact_phone', 'service_description']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Company Name'}),
            'subdomain': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'desired-subdomain'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9 Digit PAN Number'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+977-98XXXXXXXX'}),
            'service_description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'How can we help your business?', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Email will be handled in the view from the authenticated user
        self.fields['contact_email'].required = False
        self.fields['service_description'].required = False

    def clean_pan_number(self):
        pan = self.cleaned_data.get('pan_number')
        if pan and not (len(pan) == 9 and pan.isdigit()):
            raise forms.ValidationError("PAN Number must be a numeric 9-digit code.")
        return pan

    def clean_subdomain(self):
        subdomain = self.cleaned_data.get('subdomain').lower()
        if not subdomain.isalnum() and '-' not in subdomain:
            raise forms.ValidationError("Subdomain must be alphanumeric and can contain hyphens.")
        return subdomain
