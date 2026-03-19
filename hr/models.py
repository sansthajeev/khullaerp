from django.db import models
from django.conf import settings

class Employee(models.Model):
    employee_id = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=200)
    designation = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    
    # Contact Details
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    # Personal/Tax Details
    pan_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="PAN Number")
    basic_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    join_date = models.DateField(blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        if not self.employee_id:
            # Generate code: EMP-0001, EMP-0002...
            last_emp = Employee.objects.all().order_by('id').last()
            if not last_emp:
                self.employee_id = 'EMP-0001'
            else:
                last_id = last_emp.id
                self.employee_id = 'EMP-' + str(last_id + 1).zfill(4)
        super(Employee, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_id} - {self.name}"

class PayrollRun(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Finalized', 'Finalized'),
    ]
    CALENDAR_CHOICES = [
        ('AD', 'English (AD)'),
        ('BS', 'Nepali (BS)'),
    ]
    
    run_number = models.CharField(max_length=20, unique=True, editable=False)
    date = models.DateField()
    month = models.DateField(help_text="Reference month for payroll")
    calendar_type = models.CharField(max_length=5, choices=CALENDAR_CHOICES, default='AD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    
    # Financial details
    payment_ledger = models.ForeignKey('accounting.Ledger', on_delete=models.PROTECT, related_name='payroll_payments')
    salary_expense_ledger = models.ForeignKey('accounting.Ledger', on_delete=models.PROTECT, related_name='salary_expenses')
    tds_payable_ledger = models.ForeignKey('accounting.Ledger', on_delete=models.PROTECT, related_name='payroll_tds')
    
    total_gross = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_sst = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Total Social Security Tax (1%)")
    total_it = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Total Income Tax")
    total_tds = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_net = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        if not self.run_number:
            last_run = PayrollRun.objects.all().order_by('id').last()
            if not last_run:
                self.run_number = 'PAY-0001'
            else:
                last_id = last_run.id
                self.run_number = 'PAY-' + str(last_id + 1).zfill(4)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.run_number} - {self.month.strftime('%B %Y')}"

class PayrollEntry(models.Model):
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name='entries')
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT)
    
    basic_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    gross_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Bifurcated TDS
    sst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=1.00, help_text="SST % (Social Security Tax, e.g. 1%)")
    sst_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    it_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="IT % (Income Tax / Other TDS)")
    it_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    total_tds = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_payable = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        self.gross_salary = self.basic_salary + self.allowances
        self.sst_amount = (self.gross_salary * self.sst_rate) / 100
        self.it_amount = (self.gross_salary * self.it_rate) / 100
        self.total_tds = self.sst_amount + self.it_amount
        self.net_payable = self.gross_salary - self.total_tds
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.name} - {self.payroll_run.run_number}"
