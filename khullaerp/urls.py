from django.contrib import admin
from django.urls import path, include
from users.views import login_view, logout_view, register_view, dashboard_view, company_settings_view

urlpatterns = [
    # Super Admin (Hidden for emergency use)
    path('super-admin/', admin.site.urls),
    
    # Main Site & Requests
    path('', include('customers.urls')),
    
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    
    path('u/', include('users.urls')),
    
    # Custom Modules
    path('accounting/', include('accounting.urls')),
    path('inventory/', include('inventory.urls')),
    path('contacts/', include('contacts.urls')),
    path('sales/', include('sales.urls')),
    path('purchases/', include('purchases.urls')),
    path('hr/', include('hr.urls')),
    path('taxation/', include('taxation.urls')),
]
