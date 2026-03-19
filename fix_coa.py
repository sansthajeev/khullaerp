import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_neponbiz.settings')
django.setup()

from customers.models import Client
from django_tenants.utils import schema_context
from accounting.models import AccountGroup, Ledger

for tenant in Client.objects.exclude(schema_name='public'):
    with schema_context(tenant.schema_name):
        for g in AccountGroup.objects.filter(parent=None):
            if not g.code: g.save()
        for g in AccountGroup.objects.exclude(parent=None).order_by('id'):
            if not g.code: g.save()
        for l in Ledger.objects.all().order_by('id'):
            if not l.code: l.save()
        
        Ledger.ensure_core_ledgers()
        print(f"Provisioned COA for {tenant.schema_name}")
