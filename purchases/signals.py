from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import PurchaseInvoice
from accounting.models import Voucher

@receiver(pre_delete, sender=PurchaseInvoice)
def delete_related_voucher_on_purchase_bill_delete(sender, instance, **kwargs):
    """
    When a Purchase Bill is deleted, completely remove any associated Accounting Voucher.
    The linkage relies on the structured narration string generated upon creation.
    """
    if instance.bill_number:
        # The narration format is strictly 'Purchase Bill: BILL-YYYY-XXXX'
        search_string = f"Purchase Bill: {instance.bill_number}"
        
        # Find and delete matching vouchers
        Voucher.objects.filter(narration__contains=search_string).delete()
