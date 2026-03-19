from users.models import CustomUser
from django_tenants.utils import schema_context
import json

results = {}
try:
    with schema_context('acme'):
        users = list(CustomUser.objects.values('username', 'email', 'is_superuser'))
        results['users'] = users
except Exception as e:
    results['error'] = str(e)

with open('acme_debug.json', 'w') as f:
    json.dump(results, f)
