from django.db import models
from django.conf import settings

class AccountGroup(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subgroups')
    
    def save(self, *args, **kwargs):
        if not self.code:
            # Auto-coding logic for groups
            if not self.parent:
                # Top level groups based on standard accounting
                prefixes = {
                    'Assets': '1000',
                    'Liabilities': '2000',
                    'Equity': '3000',
                    'Revenue': '4000',
                    'Expenses': '5000'
                }
                self.code = prefixes.get(self.name, '9000')
            else:
                last_sub = self.parent.subgroups.order_by('code').last()
                if not last_sub:
                    self.code = f"{int(self.parent.code) + 100}"
                else:
                    self.code = f"{int(last_sub.code) + 100}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def is_liquidity_group(self):
        return self.name.lower() in ['cash', 'bank', 'cash & bank', 'cash and bank'] or (self.parent and self.parent.is_liquidity_group)

class Ledger(models.Model):
    ACCOUNT_TYPES = [
        ('Asset', 'Asset'),
        ('Liability', 'Liability'),
        ('Equity', 'Equity'),
        ('Income', 'Income'),
        ('Expense', 'Expense'),
    ]
    SUBLEDGER_CHOICES = [
        ('None', 'None'),
        ('Contact', 'Contact'),
        ('Employee', 'Employee'),
    ]
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20, unique=True, blank=True)
    group = models.ForeignKey(AccountGroup, on_delete=models.CASCADE, related_name='ledgers')
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    subledger_type = models.CharField(max_length=20, choices=SUBLEDGER_CHOICES, default='None')
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        if not self.code:
            last_ledger = self.group.ledgers.order_by('code').last()
            if not last_ledger:
                self.code = f"{int(self.group.code) + 1}"
            else:
                self.code = f"{int(last_ledger.code) + 1}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def is_liquidity(self):
        return self.group.is_liquidity_group or self.account_type in ['Asset'] and self.name.lower() in ['cash', 'bank']


    @staticmethod
    def ensure_core_ledgers():
        # Ensure Groups exist
        def get_group(name, parent=None):
            grp = AccountGroup.objects.filter(name=name, parent=parent).first()
            if not grp:
                grp = AccountGroup.objects.create(name=name, parent=parent)
            return grp

        asset_grp = get_group('Assets')
        liability_grp = get_group('Liabilities')
        revenue_grp = get_group('Revenue')
        expense_grp = get_group('Expenses')
        equity_grp = get_group('Equity')
        
        # Subgroups
        receivable_grp = get_group('Current Assets', asset_grp)
        liab_sub_grp = get_group('Current Liabilities', liability_grp)
        cash_bank_grp = get_group('Cash & Bank', receivable_grp)
        debtors_grp = get_group('Sundry Debtors', receivable_grp)
        creditors_grp = get_group('Sundry Creditors', liab_sub_grp)
        exp_operating = get_group('Operating Expenses', expense_grp)
        exp_direct = get_group('Direct Expenses', expense_grp)
        
        # Ensure Ledgers exist with explicit Sub-ledger types
        def get_ledger(name, group, account_type, subledger_type='None'):
            l = Ledger.objects.filter(name=name, group=group).first()
            if not l:
                l = Ledger.objects.create(name=name, group=group, account_type=account_type, subledger_type=subledger_type)
            return l

        get_ledger('Local Sales', revenue_grp, 'Income')
        get_ledger('Local Purchase', exp_direct, 'Expense')
        get_ledger('Sales VAT (13%)', liab_sub_grp, 'Liability')
        get_ledger('Purchase VAT (13%)', receivable_grp, 'Asset')
        
        # Accounts with Contact sub-ledgers
        get_ledger('Accounts Receivable (General)', receivable_grp, 'Asset', subledger_type='Contact')
        get_ledger('Accounts Payable (General)', creditors_grp, 'Liability', subledger_type='Contact')
        
        get_ledger('Cash in Hand', cash_bank_grp, 'Asset')
        get_ledger('Petty Cash', cash_bank_grp, 'Asset')
        get_ledger('Main Bank Account', cash_bank_grp, 'Asset')
        
        # POS Specific liquidity accounts
        get_ledger('Cash in Hand (POS)', cash_bank_grp, 'Asset')
        get_ledger('Bank Account (POS)', cash_bank_grp, 'Asset')
        
        # TDS Ledgers
        get_ledger('TDS Payable', liab_sub_grp, 'Liability')
        get_ledger('TDS Receivable', receivable_grp, 'Asset')
        
        # Standard Expenses
        get_ledger('Cost of Goods Sold', exp_direct, 'Expense')
        get_ledger('Sales Discount Given', exp_direct, 'Expense')
        get_ledger('Office Rent', exp_operating, 'Expense')
        get_ledger('Electricity & Water', exp_operating, 'Expense')
        get_ledger('Internet Expense', exp_operating, 'Expense')
        
        # Payroll with Employee sub-ledgers
        get_ledger('Salaries & Wages', exp_operating, 'Expense', subledger_type='Employee')
        get_ledger('Professional Fees', exp_operating, 'Expense')
        
        # Equity
        get_ledger('Share Capital', equity_grp, 'Equity')
        get_ledger('Retained Earnings', equity_grp, 'Equity')

        # Update existing specialized ledgers if they don't have subledger_type set
        Ledger.objects.filter(name__icontains='Debtor').update(subledger_type='Contact')
        Ledger.objects.filter(name__icontains='Creditor').update(subledger_type='Contact')
        Ledger.objects.filter(name__icontains='Salary').update(subledger_type='Employee')
        Ledger.objects.filter(name__icontains='Wage').update(subledger_type='Employee')


class Voucher(models.Model):
    VOUCHER_TYPES = [
        ('Sales', 'Sales'),
        ('Purchase', 'Purchase'),
        ('Payment', 'Payment'),
        ('Receipt', 'Receipt'),
        ('Journal', 'Journal'),
        ('Contra', 'Contra'),
    ]
    date = models.DateField()
    voucher_type = models.CharField(max_length=20, choices=VOUCHER_TYPES)
    number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    narration = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    is_finalized = models.BooleanField(default=False) # For IRD Audit Trail
    
    def save(self, *args, **kwargs):
        if not self.number:
            from django.utils import timezone
            year = timezone.now().year
            
            # Prefix mapping based on voucher type
            prefix_map = {
                'Sales': 'SALES',
                'Purchase': 'PURCH',
                'Payment': 'PAY',
                'Receipt': 'REC',
                'Journal': 'JRNL',
                'Contra': 'CONT'
            }
            prefix = prefix_map.get(self.voucher_type, 'VCH')
            
            # Find all vouchers with the prefix for the current year
            existing_vouchers = Voucher.objects.filter(number__startswith=f'{prefix}-{year}-')
            
            if not existing_vouchers.exists():
                self.number = f'{prefix}-{year}-0001'
            else:
                # Need to manually find the highest number because string sorting 'VCH-2024-2' > 'VCH-2024-10'
                max_id = 0
                for v in existing_vouchers:
                    try:
                        current_id = int(v.number.split('-')[-1])
                        if current_id > max_id:
                            max_id = current_id
                    except ValueError:
                        pass
                
                new_id = max_id + 1
                self.number = f'{prefix}-{year}-{str(new_id).zfill(4)}'
                
        super().save(*args, **kwargs)

    @property
    def total_amount(self):
        return sum(entry.debit for entry in self.entries.all() if entry.debit)

    def __str__(self):
        return f"{self.voucher_type} - {self.number}"

class VoucherEntry(models.Model):
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name='entries')
    ledger = models.ForeignKey(Ledger, on_delete=models.CASCADE)
    contact = models.ForeignKey('contacts.Contact', on_delete=models.SET_NULL, null=True, blank=True)
    employee = models.ForeignKey('hr.Employee', on_delete=models.SET_NULL, null=True, blank=True)
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.ledger.name} ({'Dr' if self.debit > 0 else 'Cr'})"
