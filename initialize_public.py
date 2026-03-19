from customers.models import Client, Domain
from django.db import connection

def initialize_public_tenant():
    # Only create if it doesn't exist
    if not Client.objects.filter(schema_name='public').exists():
        tenant = Client(schema_name='public', name='Public Tenant')
        tenant.save()
        
        domain = Domain()
        domain.domain = 'localhost' # or your domain
        domain.tenant = tenant
        domain.is_primary = True
        domain.save()
        print("Public tenant initialized.")
    else:
        print("Public tenant already exists.")

if __name__ == "__main__":
    initialize_public_tenant()
