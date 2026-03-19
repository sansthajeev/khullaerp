from django.db import models
from django.conf import settings
from accounting.models import Voucher, Ledger
from hr.models import Employee
from contacts.models import Contact

class TDSHeading(models.Model):
    code = models.CharField(max_length=20, unique=True, help_text="IRD Code e.g. 11112")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class TDSJournal(models.Model):
    # Linking to a Voucher so it results in accounting entries
    voucher = models.OneToOneField(Voucher, on_delete=models.CASCADE, related_name='tds_journal')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"TDS Journal {self.voucher.number if self.voucher else 'New'}"

class TDSJournalLine(models.Model):
    tds_journal = models.ForeignKey(TDSJournal, on_delete=models.CASCADE, related_name='tds_lines')
    
    ledger = models.ForeignKey(Ledger, on_delete=models.PROTECT)
    
    # Selection for Withholdee
    SUBLEDGER_TYPES = [
        ('None', 'None'),
        ('Employee', 'Employee'),
        ('Contact', 'Contact'),
    ]
    subledger_type = models.CharField(max_length=20, choices=SUBLEDGER_TYPES, default='None')
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True)
    
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    tds_heading = models.ForeignKey(TDSHeading, on_delete=models.SET_NULL, null=True, blank=True, related_name='tds_lines')
    
    # Extra fields for IRD reporting
    taxable_ledger = models.ForeignKey(Ledger, on_delete=models.SET_NULL, null=True, blank=True, related_name='taxed_lines')
    payment_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Line for {self.ledger.name}"
