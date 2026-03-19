from .utils import get_current_nepali_date

def nepali_date_context(request):
    return {
        'current_nepali_date': get_current_nepali_date()
    }
