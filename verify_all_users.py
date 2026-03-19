import os
import django

# SETTINGS MUST BE SETUP BEFORE IMPORTS
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_neponbiz.settings')
django.setup()

from django.db import connection
from django_tenants.utils import schema_context
from users.models import CustomUser
from customers.models import Client

def sync_verification():
    # 1. Process Public Schema
    print("--- Public Schema ---")
    with schema_context('public'):
        users = CustomUser.objects.all()
        count = users.count()
        print(f"Found {count} users.")
        for user in users:
            try:
                user.is_email_verified = True
                user.save()
                print(f"  - User {user.username}: Verified set to True")
            except Exception as e:
                print(f"  - User {user.username}: Error: {e}")

    # 2. Process all Tenants
    tenants = Client.objects.exclude(schema_name='public')
    for tenant in tenants:
        print(f"--- Tenant Schema '{tenant.schema_name}' ---")
        try:
            with schema_context(tenant.schema_name):
                users = CustomUser.objects.all()
                for user in users:
                    try:
                        user.is_email_verified = True
                        user.save()
                        print(f"  - User {user.username}: Verified set to True")
                    except Exception as e:
                        print(f"  - User {user.username}: Error: {e}")
        except Exception as e:
            print(f"Error accessing schema {tenant.schema_name}: {e}")

if __name__ == "__main__":
    sync_verification()
