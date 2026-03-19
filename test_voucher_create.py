import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()

    from accounting.models import Voucher
    from django.utils import timezone

    try:
        print("Creating voucher...")
        v = Voucher(date=timezone.now(), voucher_type='Sales', narration='Test dynamic number again')
        v.save()
        print(f"Success: {v.number}")
    except Exception as e:
        import traceback
        print("FAILED WITH ERROR:")
        traceback.print_exc()

if __name__ == '__main__':
    main()
