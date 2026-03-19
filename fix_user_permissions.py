import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','erp_neponbiz.settings')
django.setup()
from django_tenants.utils import schema_context
from users.models import CustomUser
from customers.models import Client

schema_name = 'sanjeev'
email = 'sanjeevshrestha183@gmail.com'

try:
    client = Client.objects.get(schema_name=schema_name)
    with schema_context(client.schema_name):
        user = CustomUser.objects.filter(email=email).first()
        if user:
            user.is_staff = True
            user.is_merchant = True
            user.save()
            print(f"Successfully updated permissions for {user.email}")
            print(f"is_staff: {user.is_staff}")
            print(f"is_merchant: {user.is_merchant}")
        else:
            print(f"User with email {email} not found in schema {schema_name}")
except Client.DoesNotExist:
    print(f"Client with schema {schema_name} not found")
except Exception as e:
    print(f"Error: {e}")
