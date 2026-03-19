from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('verify-email/<uidb64>/<token>/', views.verify_email_view, name='verify_email'),
    path('status/', views.status_dashboard_view, name='status_dashboard'),
    path('settings/', views.company_settings_view, name='company_settings'),
    
    # User Management
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('users/<int:pk>/welcome-email/', views.send_welcome_email_view, name='send_welcome_email'),
    
    # Role Management
    path('roles/', views.role_list, name='role_list'),
    path('roles/add/', views.role_create, name='role_create'),
    path('roles/preload/', views.preload_roles, name='role_preload'),
    path('roles/<int:pk>/edit/', views.role_edit, name='role_edit'),
    path('roles/<int:pk>/delete/', views.role_delete, name='role_delete'),
]
