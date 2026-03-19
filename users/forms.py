from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UsernameField
from .models import CustomUser, Role

class PublicUserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = CustomUser
        fields = ("first_name", "last_name", "email", "password")

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(username=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = [
            'name', 'description', 
            'can_access_accounting', 'can_access_inventory', 
            'can_access_sales', 'can_access_purchases', 
            'can_access_hr', 'can_access_taxation', 'can_manage_users'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Sales Manager'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional description of responsibilities...'}),
        }

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("first_name", "last_name", "username", "email", "phone_number", "role")
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field != 'role':
                self.fields[field].widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': f"Enter {self.fields[field].label}"
                })
        
        self.fields['role'].widget.attrs.update({'class': 'form-select'})
        
        # Specific help text refinement
        if 'username' in self.fields:
            self.fields['username'].help_text = "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email or Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}))

    def clean(self):
        username = self.cleaned_data.get('username')
        if username and '@' in username:
            # Try to find user by email
            user = CustomUser.objects.filter(email=username).first()
            if user:
                self.cleaned_data['username'] = user.username
        return super().clean()
class CustomUserEditForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ("first_name", "last_name", "email", "phone_number", "is_staff", "is_active", "role")
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
        }
