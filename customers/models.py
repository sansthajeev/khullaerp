from django.db import models
from django_tenants.models import TenantMixin, DomainMixin

class Client(TenantMixin):
    name = models.CharField(max_length=100)
    created_on = models.DateField(auto_now_add=True)

    # Company Settings
    is_vat_registered = models.BooleanField(default=True, verbose_name="VAT Registered")
    pan_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="PAN/VAT Number")
    default_vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=13.00, verbose_name="Default VAT Rate (%)")
    uses_inventory = models.BooleanField(default=True, verbose_name="Uses Inventory Module")

    # default true, schema will be automatically created and synced when it is saved
    auto_create_schema = True

    def __str__(self):
        return self.name

class Domain(DomainMixin):
    pass

class TenantRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    company_name = models.CharField(max_length=100)
    subdomain = models.SlugField(max_length=50, unique=True)
    pan_number = models.CharField(max_length=20, verbose_name="PAN Number", default='')
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='tenant_requests', null=True, blank=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    service_description = models.TextField(blank=True, help_text="Briefly describe your business needs")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.company_name} ({self.subdomain})"
