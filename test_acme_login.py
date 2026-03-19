from users.models import CustomUser
from django_tenants.utils import schema_context
from django.contrib.auth import authenticate

print("--- Checking Acme Schema ---")
with schema_context('acme'):
    user = CustomUser.objects.filter(username='admin_acme').first()
    if user:
        print(f"User 'admin_acme' exists.")
        print(f"Email: {user.email}")
        print(f"Is active: {user.is_active}")
        print(f"Is superuser: {user.is_superuser}")
        
        # Test authentication
        auth_user = authenticate(username='admin_acme', password='password123')
        if auth_user:
            print("Authentication SUCCESS for 'admin_acme' / 'password123'")
        else:
            print("Authentication FAILED for 'admin_acme' / 'password123'")
            
        # Check if login with email works (it shouldn't by default)
        auth_email = authenticate(username='investof.sanjeev@gmail.com', password='password123')
        if auth_email:
            print("Authentication SUCCESS for email 'investof.sanjeev@gmail.com'")
        else:
            print("Authentication FAILED for email 'investof.sanjeev@gmail.com'")
    else:
        print("User 'admin_acme' does NOT exist in acme schema.")
        all_users = list(CustomUser.objects.values_list('username', flat=True))
        print(f"Available users: {all_users}")
