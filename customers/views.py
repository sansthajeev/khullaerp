from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django_tenants.utils import schema_context
from django.utils import timezone
from .models import Client, Domain, TenantRequest
from .forms import ClientForm, TenantRequestForm
from users.models import CustomUser
from users.forms import CustomUserCreationForm
from django_celery_results.models import TaskResult
from .tasks import send_request_received_email, send_admin_notification_email, send_approval_email

def is_superuser(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_superuser)
def celery_logs(request):
    logs = TaskResult.objects.all().order_by('-date_done')
    return render(request, 'customers/celery_logs.html', {'logs': logs})

from django.contrib.auth import login, authenticate
from users.forms import PublicUserCreationForm, CustomAuthenticationForm

def landing_page(request):
    if request.user.is_authenticated and request.tenant.schema_name == 'public':
        # If already logged in on public, they should see request form or dashboard
        pass

    if request.method == 'POST':
        action = request.POST.get('action_type')
        
        if action == 'login':
            form = CustomAuthenticationForm(request, data=request.POST)
            if form.is_valid():
                user = form.get_user()
                if not user.is_superuser and not user.is_email_verified:
                    messages.warning(request, "Please verify your email address before logging in.")
                    return redirect('customers:landing_page')
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect('users:dashboard')
            else:
                messages.error(request, "Invalid email or password.")
                return redirect('customers:landing_page')

        elif action == 'register':
            form = PublicUserCreationForm(request.POST)
            if form.is_valid():
                user = form.save(commit=False)
                user.is_active = True
                user.save()
                from users.tasks import send_verification_email
                send_verification_email.delay(user.id, request.get_host())
                messages.success(request, "Registration successful! Please check your email to verify.")
                return redirect('customers:landing_page')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field.capitalize()}: {error}")
                        break
                    break
                return redirect('customers:landing_page')

        elif action == 'tenant_request':
            form = TenantRequestForm(request.POST)
            if form.is_valid():
                tenant_req = form.save(commit=False)
                if request.user.is_authenticated:
                    tenant_req.user = request.user
                    tenant_req.contact_email = request.user.email
                tenant_req.save()
                send_request_received_email.delay(tenant_req.contact_email, tenant_req.company_name)
                send_admin_notification_email.delay(tenant_req.company_name, tenant_req.subdomain)
                messages.success(request, "Request submitted successfully!")
                return redirect('users:status_dashboard')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field.capitalize()}: {error}")
                        break
                    break
                return redirect('customers:landing_page')
    
    # GET request logic
    tenant_form = TenantRequestForm()
    return render(request, 'public/landing_page.html', {
        'form': tenant_form,
        'login_form': CustomAuthenticationForm(),
        'register_form': PublicUserCreationForm()
    })

@user_passes_test(is_superuser)
def tenant_request_list(request):
    requests = TenantRequest.objects.all().order_by('-created_at')
    return render(request, 'customers/tenant_request_list.html', {'tenant_requests': requests})

@user_passes_test(is_superuser)
def tenant_request_approve(request, pk):
    tenant_req = get_object_or_404(TenantRequest, pk=pk)
    if tenant_req.status == 'PENDING':
        try:
            # 1. Create the Client (Tenant) idempotently
            client, created = Client.objects.get_or_create(
                schema_name=tenant_req.subdomain,
                defaults={
                    'name': tenant_req.company_name,
                    'pan_number': tenant_req.pan_number
                }
            )
            
            # 2. Create the Domain idempotently
            Domain.objects.get_or_create(
                tenant=client,
                domain=f"{tenant_req.subdomain}.localhost", # Adjust for production
                defaults={'is_primary': True}
            )
            
            # Pre-fetch user info before switching schema context
            first_name = "Store"
            last_name = "Owner"
            if tenant_req.user:
                first_name = tenant_req.user.first_name
                last_name = tenant_req.user.last_name

            # 3. Create the Initial Admin User within the tenant schema
            with schema_context(client.schema_name):
                # We set a temporary password for the new tenant-specific admin
                temp_password = "password123" 
                admin_username = f"admin_{tenant_req.subdomain}"
                if not CustomUser.objects.filter(username=admin_username).exists():
                    new_user = CustomUser.objects.create_superuser(
                        username=admin_username,
                        email=tenant_req.contact_email,
                        password=temp_password,
                        first_name=first_name,
                        last_name=last_name,
                        is_active=True,
                        is_staff=True,
                        is_merchant=True
                    )
            
            tenant_req.status = 'APPROVED'
            tenant_req.reviewed_at = timezone.now()
            tenant_req.save()
            
            # Send approval email with credentials
            send_approval_email.delay(
                tenant_req.contact_email,
                tenant_req.company_name,
                tenant_req.subdomain,
                f"admin_{tenant_req.subdomain}",
                temp_password
            )
            
            messages.success(request, f"Tenant '{tenant_req.company_name}' approved and created successfully!")
        except Exception as e:
            messages.error(request, f"Error approving tenant: {e}")
            
    return redirect('customers:tenant_request_list')

@user_passes_test(is_superuser)
def tenant_request_resend_welcome(request, pk):
    tenant_req = get_object_or_404(TenantRequest, pk=pk)
    if tenant_req.status == 'APPROVED':
        try:
            # We use the standard temp password
            temp_password = "password123"
            
            # Send approval email again
            send_approval_email.delay(
                tenant_req.contact_email,
                tenant_req.company_name,
                tenant_req.subdomain,
                f"admin_{tenant_req.subdomain}",
                temp_password
            )
            messages.success(request, f"Welcome email resent to {tenant_req.contact_email}")
        except Exception as e:
            messages.error(request, f"Error resending email: {e}")
    else:
        messages.error(request, "Only approved requests can have welcome emails resent.")
        
    return redirect('customers:tenant_request_list')

@user_passes_test(is_superuser)
def client_list(request):
    clients = Client.objects.exclude(schema_name='public')
    return render(request, 'customers/client_list.html', {'clients': clients})

@user_passes_test(is_superuser)
def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            try:
                # Create the client (tenant)
                client = form.save()
                
                # Create the domain for the client
                domain_name = form.cleaned_data.get('domain_name')
                Domain.objects.create(
                    domain=domain_name,
                    tenant=client,
                    is_primary=True
                )
                
                messages.success(request, f"Company '{client.name}' created successfully with domain {domain_name}.")
                return redirect('customers:client_list')
            except Exception as e:
                messages.error(request, f"Error creating company: {e}")
    else:
        form = ClientForm()
    
    return render(request, 'customers/client_create.html', {'form': form})

@user_passes_test(is_superuser)
def tenant_user_list(request, tenant_pk):
    client = get_object_or_404(Client, pk=tenant_pk)
    with schema_context(client.schema_name):
        users = list(CustomUser.objects.all())
    return render(request, 'customers/tenant_user_list.html', {
        'client': client,
        'tenant_users': users
    })

@user_passes_test(is_superuser)
def tenant_user_create(request, tenant_pk):
    client = get_object_or_404(Client, pk=tenant_pk)
    if request.method == 'POST':
        with schema_context(client.schema_name):
            form = CustomUserCreationForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, f"User created successfully in {client.name}.")
                return redirect('customers:tenant_user_list', tenant_pk=tenant_pk)
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'customers/tenant_user_create.html', {
        'client': client,
        'form': form
    })

@user_passes_test(is_superuser)
def tenant_user_edit(request, tenant_pk, user_id):
    client = get_object_or_404(Client, pk=tenant_pk)
    with schema_context(client.schema_name):
        tenant_user = get_object_or_404(CustomUser, pk=user_id)
        if request.method == 'POST':
            tenant_user.is_active = request.POST.get('is_active') == 'on'
            tenant_user.is_staff = request.POST.get('is_staff') == 'on'
            tenant_user.save()
            messages.success(request, f"User {tenant_user.username} updated in {client.name}.")
            return redirect('customers:tenant_user_list', tenant_pk=tenant_pk)
        
    return render(request, 'customers/tenant_user_edit.html', {
        'client': client,
        'tenant_user': tenant_user
    })

@user_passes_test(is_superuser)
def tenant_user_delete(request, tenant_pk, user_id):
    client = get_object_or_404(Client, pk=tenant_pk)
    with schema_context(client.schema_name):
        tenant_user = get_object_or_404(CustomUser, pk=user_id)
        username = tenant_user.username
        tenant_user.delete()
        messages.warning(request, f"User {username} deleted from {client.name}.")
    return redirect('customers:tenant_user_list', tenant_pk=tenant_pk)
