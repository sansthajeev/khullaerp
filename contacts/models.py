from django.db import models
from django.conf import settings

class Contact(models.Model):
    CONTACT_TYPES = [
        ('Customer', 'Customer'),
        ('Supplier', 'Supplier'),
        ('Both', 'Both'),
    ]
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True, editable=False, null=True)
    contact_type = models.CharField(max_length=20, choices=CONTACT_TYPES, default='Customer')
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    # Tax Details (Nepali Specific)
    pan_vat_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="PAN/VAT Number")
    
    # For accounting integration
    # ledger = models.OneToOneField('accounting.Ledger', on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        if not self.code:
            # Generate code: CON-0001, CON-0002...
            last_contact = Contact.objects.all().order_by('id').last()
            if not last_contact:
                self.code = 'CON-0001'
            else:
                last_id = last_contact.id
                self.code = 'CON-' + str(last_id + 1).zfill(4)
        super(Contact, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"
