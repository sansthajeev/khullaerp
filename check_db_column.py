import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_neponbiz.settings')
django.setup()

def check_column():
    with connection.cursor() as cursor:
        # Check public schema
        cursor.execute("SET search_path TO public")
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users_customuser' AND column_name='is_email_verified'")
        res = cursor.fetchone()
        print(f"Public schema: {'Found' if res else 'MISSING'}")

        # Check all schemas
        cursor.execute("SELECT schema_name FROM customers_client")
        schemas = [row[0] for row in cursor.fetchall()]
        for schema in schemas:
            if schema == 'public': continue
            try:
                cursor.execute(f"SET search_path TO {schema}")
                cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='users_customuser' AND column_name='is_email_verified'")
                res = cursor.fetchone()
                print(f"Schema {schema}: {'Found' if res else 'MISSING'}")
            except Exception as e:
                print(f"Schema {schema}: Error {e}")

if __name__ == "__main__":
    check_column()
