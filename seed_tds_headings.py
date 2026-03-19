import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_neponbiz.settings')
django.setup()

from taxation.models import TDSHeading
from customers.models import Client

def seed_schema(schema_name):
    if schema_name == 'public':
        print("Skipping public schema for taxation seeding.")
        return
        
    print(f"Seeding schema: {schema_name}")
    connection.set_schema(schema_name)
    
    headings = [
        {'code': '11111', 'name': 'Proprietorship Tax and Individual Income tax'},
        {'code': '11112', 'name': 'Remuneration Tax'},
        {'code': '11113', 'name': 'Capital Gain Tax - Individual'},
        {'code': '11121', 'name': 'Government Organization Income Tax'},
        {'code': '11122', 'name': 'Public Company Income Tax'},
        {'code': '11123', 'name': 'Private Company Income Tax'},
        {'code': '11124', 'name': 'Other Organization Income Tax'},
        {'code': '11125', 'name': 'Capital Gain Tax - Entity'},
        {'code': '11311', 'name': 'Interest Tax'},
        {'code': '11411', 'name': 'Rent Tax'},
        {'code': '11421', 'name': 'Royalty Tax'},
    ]

    for h in headings:
        obj, created = TDSHeading.objects.get_or_create(code=h['code'], defaults={'name': h['name']})
        if created:
            print(f"  Created: {h['name']} ({h['code']})")
        else:
            print(f"  Exists: {h['name']} ({h['code']})")

# Seed all tenants
connection.set_schema('public')
for tenant in Client.objects.all():
    seed_schema(tenant.schema_name)
