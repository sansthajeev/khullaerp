from django import template
import nepali_datetime
import datetime

register = template.Library()

@register.filter(name='to_nepali')
def to_nepali(value, format_string='%Y-%m-%d'):
    """
    Converts a Python datetime.date or datetime.datetime object to a Nepali Date string.
    Usage in template: {{ user.date_joined|to_nepali:"%Y %B %d" }}
    Default format: YYYY-MM-DD
    """
    if not value:
        return ''

    # Handle if it's a datetime object (convert to date first)
    if isinstance(value, datetime.datetime):
        value = value.date()

    if isinstance(value, datetime.date):
        try:
            np_date = nepali_datetime.date.from_datetime_date(value)
            
            # Use custom nepali-datetime formatting
            # Check nepali-datetime docs for specific format codes if needed,
            # standard strftime codes generally work for basics (%Y, %m, %d)
            # Some custom codes: %K (year), %n (month number), %N (month name), %D (day)
            
            # Map common strftime codes for ease of use
            # Example conversion: %Y-%m-%d -> %K-%n-%D
            format_string = format_string.replace('%Y', '%K').replace('%m', '%n').replace('%d', '%D').replace('%B', '%N')
            
            return np_date.strftime(format_string)
        except Exception as e:
            # Fallback to string representation if formatting fails
            try:
                np_date = nepali_datetime.date.from_datetime_date(value)
                return str(np_date)
            except:
                 return str(value)
                 
    return value
@register.filter
def abs_val(value):
    """Returns the absolute value of a number."""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value

@register.filter
def subtract(value, arg):
    """Subtracts the arg from the value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def multiply(value, arg):
    """Multiplies the value by the arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def indian_intl(value):
    """
    Formats a number according to the Indian/Nepali numbering system (Lakh/Crore).
    Example: 123456.78 -> 1,23,456.78
    """
    try:
        if value is None:
            return "0.00"
        
        # Ensure it's a float/decimal
        float_val = float(value)
        
        # Split integer and decimal parts
        parts = "{:.2f}".format(float_val).split('.')
        int_part = parts[0]
        dec_part = parts[1]
        
        # Handle negative sign
        sign = ""
        if int_part.startswith('-'):
            sign = "-"
            int_part = int_part[1:]
            
        # Reverse the integer part for easier grouping
        rev_int = int_part[::-1]
        
        groups = []
        # First group is 3 digits
        groups.append(rev_int[:3])
        # Subsequent groups are 2 digits
        remaining = rev_int[3:]
        for i in range(0, len(remaining), 2):
            groups.append(remaining[i:i+2])
            
        # Join with commas and reverse back
        formatted_int = ",".join(groups)[::-1]
        
        return f"{sign}{formatted_int}.{dec_part}"
    except (ValueError, TypeError):
        return value
