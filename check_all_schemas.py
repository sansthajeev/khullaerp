import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_neponbiz.settings')
django.setup()

def list_all_schemas():
    with connection.cursor() as cursor:
        cursor.execute("SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname != 'information_schema'")
        schemas = [row[0] for row in cursor.fetchall()]
        print(f"All schemas in DB: {schemas}")
        
        for schema in schemas:
            try:
                cursor.execute(f"SET search_path TO {schema}")
                cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users_customuser')")
                has_table = cursor.fetchone()[0]
                if has_table:
                    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users_customuser' AND column_name='is_email_verified'")
                    res = cursor.fetchone()
                    print(f"Schema {schema}: users_customuser exists, is_email_verified {'Found' if res else 'MISSING'}")
                else:
                    print(f"Schema {schema}: users_customuser NOT found")
            except Exception as e:
                print(f"Schema {schema}: Error {e}")

if __name__ == "__main__":
    list_all_schemas()
