from customers.models import TenantRequest, Client
from users.models import CustomUser
from django_tenants.utils import schema_context

print("--- Request Info ---")
tr = TenantRequest.objects.filter(subdomain='acme').last()
if tr:
    print(f"Company: {tr.company_name}")
    print(f"Contact Email: {tr.contact_email}")
    print(f"Status: {tr.status}")
else:
    print("No TenantRequest found for 'acme'")

print("\n--- Tenant Users ---")
try:
    with schema_context('acme'):
        users = CustomUser.objects.all()
        if users:
            for user in users:
                print(f"Email: {user.email}, Username: {user.username}, Superuser: {user.is_superuser}")
        else:
            print("No users found in 'acme' schema")
except Exception as e:
    print(f"Error: {e}")
