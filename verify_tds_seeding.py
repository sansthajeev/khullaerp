import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','erp_neponbiz.settings')
django.setup()
from django_tenants.utils import schema_context
from taxation.models import TDSHeading
from taxation.utils import seed_default_tds_headings
from customers.models import Client

schema_name = 'sanjeev'

try:
    client = Client.objects.get(schema_name=schema_name)
    with schema_context(client.schema_name):
        # Count before seeding
        before_count = TDSHeading.objects.count()
        print(f"Count before seeding: {before_count}")
        
        # Run seed
        seed_default_tds_headings()
        
        # Count after seeding
        after_count = TDSHeading.objects.count()
        print(f"Count after seeding: {after_count}")
        
        if after_count >= 40:
            print("Successfully seeded revenue codes!")
            # Check for a specific code
            h = TDSHeading.objects.filter(code='11412').first()
            if h:
                print(f"Found Code 11412: {h.name}")
                print(f"Description: {h.description[:50]}...")
            else:
                print("Code 11412 not found!")
        else:
            print(f"Seeding failed. Expected > 40, found {after_count}")
except Exception as e:
    print(f"Error: {e}")
