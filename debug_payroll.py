import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_neponbiz.settings')
django.setup()

from hr.forms import PayrollEntryForm

print("--- Meta Fields ---")
for f in PayrollEntryForm.Meta.fields:
    print(f)

from hr.models import PayrollEntry
print("--- Model Fields ---")
for f in PayrollEntry._meta.get_fields():
    print(f.name)
