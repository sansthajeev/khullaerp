import nepali_datetime
from decimal import Decimal

def get_current_nepali_date():
    """Returns today's date in Bikram Sambat (B.S.)"""
    now_ad = nepali_datetime.datetime.now()
    return now_ad.strftime("%d %B %Y") # Example: 14 Falgun 2080

def calculate_vat(amount, rate=Decimal('13.00')):
    """Calculates VAT amount based on given total and rate"""
    if not isinstance(rate, Decimal):
        rate = Decimal(str(rate))
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    
    vat_amount = amount * (rate / 100)
    total_with_vat = amount + vat_amount
    return {
        'base_amount': amount,
        'vat_rate': rate,
        'vat_amount': vat_amount,
        'total_amount': total_with_vat
    }

def ad_to_bs(date_ad):
    """Converts a standard Python date (A.D.) to Nepali Date (B.S.)"""
    if not date_ad:
        return ""
    date_bs = nepali_datetime.date.from_datetime_date(date_ad)
    return date_bs.strftime("%d %B %Y")
