from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from django.db.models.functions import TruncMonth
from django.utils import timezone
from .forms import CustomUserCreationForm, CustomAuthenticationForm, RoleForm, PublicUserCreationForm
from .models import CustomUser, Role
from .tasks import send_verification_email
from customers.models import Client, TenantRequest
from contacts.models import Contact
from inventory.models import Item
from sales.models import Invoice
from purchases.models import PurchaseInvoice
from accounting.models import Voucher
import json

@login_required
def company_settings_view(request):
    tenant = request.tenant
    if request.method == 'POST':
        tenant.is_vat_registered = request.POST.get('is_vat_registered') == 'on'
        tenant.default_vat_rate = request.POST.get('default_vat_rate', 13.00)
        tenant.uses_inventory = request.POST.get('uses_inventory') == 'on'
        tenant.save()
        messages.success(request, "Company settings updated successfully.")
        return redirect('company_settings')
    
    return render(request, 'users/company_settings.html', {'tenant': tenant})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('users:dashboard')
        
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # Check verification on public schema
            if request.tenant.schema_name == 'public' and not user.is_superuser:
                if not user.is_email_verified:
                    messages.warning(request, "Please verify your email address before logging in.")
                    return redirect('customers:landing_page')
            
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('users:dashboard')
        messages.error(request, "Invalid email or password.")
        return redirect('customers:landing_page')
    else:
        form = CustomAuthenticationForm()
    return redirect('customers:landing_page')

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('users:dashboard')
        
    if request.method == 'POST':
        form = PublicUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True # We want them to be able to log in but limited if not verified
            user.save()
            
            # Send verification email
            current_site = request.get_host()
            send_verification_email.delay(user.id, current_site)
            
            messages.success(request, "Registration successful! Please check your email to verify your account.")
            return redirect('customers:landing_page')
        # Display first form error as a message
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field.capitalize()}: {error}")
                break
            break
        return redirect('customers:landing_page')
    form = CustomUserCreationForm()
    return redirect('customers:landing_page')

def verify_email_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_email_verified = True
        user.save()
        messages.success(request, "Email verified successfully! You can now log in.")
        return redirect('login')
    else:
        messages.error(request, "The verification link is invalid or has expired.")
        return redirect('login')

def status_dashboard_view(request):
    if not request.user.is_authenticated:
        return redirect('customers:landing_page')
    
    if request.method == 'POST':
        # Handled email resend
        from .tasks import send_verification_email
        send_verification_email.delay(request.user.id, request.get_host())
        messages.success(request, f"Verification email resent to {request.user.email}")
        return redirect('users:status_dashboard')

    tenant_requests = TenantRequest.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'public/status_dashboard.html', {'tenant_requests': tenant_requests})

def dashboard_view(request):
    if request.user.is_authenticated:
        # If public schema and NOT superuser, redirect to status dashboard
        if request.tenant.schema_name == 'public' and not request.user.is_superuser:
            return redirect('users:status_dashboard')
            
    if request.tenant.schema_name == 'public':
        tenant_count = Client.objects.exclude(schema_name='public').count()
        return render(request, 'admin/saas_dashboard.html', {'tenant_count': tenant_count})
    else:
        # Tenant Dashboard
        customer_count = Contact.objects.filter(contact_type__in=['Customer', 'Both']).count()
        item_count = Item.objects.count()
        
        # Calculate Total Revenue from Finalized Invoices
        total_revenue = Invoice.objects.filter(status='Finalized').aggregate(
            total=Sum('grand_total')
        )['total'] or 0
        invoice_count = Invoice.objects.count()
        recent_invoices = Invoice.objects.all().order_by('-created_at')[:5]
        
        # Calculate Total Purchases from Finalized Invoices
        total_purchases = PurchaseInvoice.objects.filter(status='Finalized').aggregate(
            total=Sum('grand_total')
        )['total'] or 0
        purchase_count = PurchaseInvoice.objects.count()
        recent_purchases = PurchaseInvoice.objects.all().order_by('-created_at')[:5]
        
        # Monthly Chart Data for current year
        current_year = timezone.now().year
        
        # Sales per month
        sales_by_month = Invoice.objects.filter(
            status='Finalized',
            date__year=current_year
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('grand_total')
        ).order_by('month')

        # Purchases per month
        purchases_by_month = PurchaseInvoice.objects.filter(
            status='Finalized',
            date__year=current_year
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('grand_total')
        ).order_by('month')

        # Format for Chart.js
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        sales_data = [0] * 12
        purchases_data = [0] * 12

        for entry in sales_by_month:
            if entry['month']:
                month_idx = entry['month'].month - 1
                sales_data[month_idx] = float(entry['total'])
                
        for entry in purchases_by_month:
            if entry['month']:
                month_idx = entry['month'].month - 1
                purchases_data[month_idx] = float(entry['total'])

        chart_data = json.dumps({
            'labels': months,
            'sales': sales_data,
            'purchases': purchases_data
        })
        
        # Calculate Net Flow
        net_flow = total_revenue - total_purchases
        
        # Recent Vouchers
        recent_vouchers = Voucher.objects.all().order_by('-date', '-id')[:5]

        return render(request, 'admin/dashboard.html', {
            'customer_count': customer_count,
            'item_count': item_count,
            'total_revenue': total_revenue,
            'total_purchases': total_purchases,
            'net_flow': net_flow,
            'invoice_count': invoice_count,
            'purchase_count': purchase_count,
            'recent_invoices': recent_invoices,
            'recent_purchases': recent_purchases,
            'recent_vouchers': recent_vouchers,
            'chart_data': chart_data
        })

from django.shortcuts import get_object_or_404
from .models import CustomUser
from .forms import CustomUserEditForm

def is_merchant_or_admin(user):
    return user.is_authenticated and (user.is_merchant or user.is_superuser)

@user_passes_test(is_merchant_or_admin)
def user_list(request):
    users = CustomUser.objects.all().order_by('-id')
    return render(request, 'users/user_list.html', {'users': users})

@user_passes_test(is_merchant_or_admin)
def user_create(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"User {user.username} created successfully.")
            return redirect('user_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/user_form.html', {'form': form, 'title': 'Add New User'})

@user_passes_test(is_merchant_or_admin)
def user_edit(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        form = CustomUserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f"User {user.username} updated successfully.")
            return redirect('users:user_list')
    else:
        form = CustomUserEditForm(instance=user)
    return render(request, 'users/user_form.html', {'form': form, 'title': f'Edit User: {user.username}'})

@user_passes_test(is_merchant_or_admin)
def send_welcome_email_view(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        from .tasks import send_welcome_email
        # We need a password to send. Since we don't store plain text, 
        # for existing users we might need to reset it or ask admin for a temp one.
        # For now, we'll use a placeholder or handle it via a prompt if possible.
        # But wait, create_superuser used 'password123'. 
        password = request.POST.get('password', 'password123') 
        
        domain = request.get_host()
        company_name = None
        if request.tenant.schema_name != 'public':
            company_name = request.tenant.name
            
        send_welcome_email.delay(user.id, password, domain, company_name)
        messages.success(request, f"Welcome email queued for {user.email}")
        
    return redirect('users:user_list')

@user_passes_test(is_merchant_or_admin)
def user_delete(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    if user == request.user:
        messages.error(request, "You cannot delete yourself.")
    else:
        username = user.username
        user.delete()
        messages.warning(request, f"User {username} has been deleted.")
    return redirect('user_list')
@user_passes_test(is_merchant_or_admin)
def role_list(request):
    roles = Role.objects.all().order_by('name')
    return render(request, 'users/role_list.html', {'roles': roles})

@user_passes_test(is_merchant_or_admin)
def role_create(request):
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save()
            messages.success(request, f"Role '{role.name}' created successfully.")
            return redirect('role_list')
    else:
        form = RoleForm()
    return render(request, 'users/role_form.html', {'form': form, 'title': 'Define New Role'})

@user_passes_test(is_merchant_or_admin)
def role_edit(request, pk):
    role = get_object_or_404(Role, pk=pk)
    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()
            messages.success(request, f"Role '{role.name}' updated successfully.")
            return redirect('role_list')
    else:
        form = RoleForm(instance=role)
    return render(request, 'users/role_form.html', {'form': form, 'title': f'Edit Role: {role.name}'})

@user_passes_test(is_merchant_or_admin)
def role_delete(request, pk):
    role = get_object_or_404(Role, pk=pk)
    if role.users.exists():
        messages.error(request, f"Cannot delete role '{role.name}' because it is assigned to users.")
    else:
        name = role.name
        role.delete()
        messages.warning(request, f"Role '{name}' has been deleted.")
    return redirect('role_list')

@user_passes_test(is_merchant_or_admin)
def preload_roles(request):
    """Seed standard roles for the tenant."""
    default_roles = [
        {
            'name': 'Accountant',
            'description': 'Full access to accounting, taxation, and financial reports.',
            'perms': {
                'can_access_accounting': True,
                'can_access_taxation': True,
            }
        },
        {
            'name': 'Sales Executive',
            'description': 'Quick POS and Sales Invoicing access.',
            'perms': {
                'can_access_sales': True,
            }
        },
        {
            'name': 'Inventory Manager',
            'description': 'Full control over stock items, adjustments, and inventory reports.',
            'perms': {
                'can_access_inventory': True,
                'can_access_purchases': True,
            }
        },
        {
            'name': 'HR Analyst',
            'description': 'Access to employee records and HR-related data.',
            'perms': {
                'can_access_hr': True,
            }
        },
        {
            'name': 'Store Keeper',
            'description': 'Limited access to view stock and handle purchases.',
            'perms': {
                'can_access_inventory': True,
                'can_access_purchases': True,
            }
        },
        {
            'name': 'Branch Admin',
            'description': 'Full access to all modules and user management.',
            'perms': {
                'can_access_accounting': True,
                'can_access_inventory': True,
                'can_access_sales': True,
                'can_access_purchases': True,
                'can_access_hr': True,
                'can_access_taxation': True,
                'can_manage_users': True,
            }
        }
    ]
    
    created_count = 0
    skipped_count = 0
    
    for r_data in default_roles:
        role, created = Role.objects.get_or_create(
            name=r_data['name'],
            defaults={
                'description': r_data['description'],
                **r_data['perms']
            }
        )
        if created:
            created_count += 1
        else:
            skipped_count += 1
            
    if created_count > 0:
        messages.success(request, f"Successfully preloaded {created_count} standard roles.")
    if skipped_count > 0:
        messages.info(request, f"{skipped_count} roles already existed and were skipped.")
        
    return redirect('role_list')
