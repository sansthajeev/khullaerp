from django.urls import path
from . import views

app_name = 'hr'

urlpatterns = [
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/new/', views.employee_create, name='employee_create'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
]
