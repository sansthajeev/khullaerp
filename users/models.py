from django.contrib.auth.models import AbstractUser
from django.db import models

class Role(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    # Module Permissions
    can_access_accounting = models.BooleanField(default=False)
    can_access_inventory = models.BooleanField(default=False)
    can_access_sales = models.BooleanField(default=False)
    can_access_purchases = models.BooleanField(default=False)
    can_access_hr = models.BooleanField(default=False)
    can_access_taxation = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

class CustomUser(AbstractUser):
    # Add any extra fields here
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_merchant = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    
    def __str__(self):
        return self.username
