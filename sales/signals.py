from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import Invoice
from accounting.models import Voucher

@receiver(pre_delete, sender=Invoice)
def delete_related_voucher_on_invoice_delete(sender, instance, **kwargs):
    """
    When a Sales Invoice is deleted, completely remove any associated Accounting Voucher.
    The linkage relies on the structured narration string generated upon creation.
    """
    if instance.invoice_number:
        # The narration format is strictly 'Sales Invoice: INV-YYYY-XXXX'
        search_string = f"Sales Invoice: {instance.invoice_number}"
        
        # Find and delete matching vouchers
        Voucher.objects.filter(narration__contains=search_string).delete()
