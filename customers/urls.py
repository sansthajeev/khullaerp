from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    # Public Landing Page
    path('', views.landing_page, name='landing_page'),
    
    # Tenant Management
    path('tenants/', views.client_list, name='client_list'),
    path('tenants/create/', views.client_create, name='client_create'),
    path('tenants/<int:tenant_pk>/users/', views.tenant_user_list, name='tenant_user_list'),
    path('tenants/<int:tenant_pk>/users/create/', views.tenant_user_create, name='tenant_user_create'),
    path('tenants/<int:tenant_pk>/users/<int:user_id>/edit/', views.tenant_user_edit, name='tenant_user_edit'),
    path('tenants/<int:tenant_pk>/users/<int:user_id>/delete/', views.tenant_user_delete, name='tenant_user_delete'),
    
    # System & Request Management
    path('system/logs/', views.celery_logs, name='celery_logs'),
    path('requests/', views.tenant_request_list, name='tenant_request_list'),
    path('requests/<int:pk>/approve/', views.tenant_request_approve, name='tenant_request_approve'),
    path('requests/<int:pk>/resend-welcome/', views.tenant_request_resend_welcome, name='tenant_request_resend_welcome'),
]
