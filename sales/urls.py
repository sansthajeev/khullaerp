from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('', views.invoice_list, name='invoice_list'),
    path('create/', views.invoice_create, name='invoice_create'),
    path('<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('<int:pk>/edit/', views.invoice_edit, name='invoice_edit'),
    path('invoices/<int:pk>/delete/', views.invoice_delete, name='invoice_delete'),
    
    # POS System
    path('pos/', views.pos_view, name='pos_view'),
    path('pos/search-items/', views.pos_item_search, name='pos_item_search'),
    path('pos/submit/', views.pos_submit, name='pos_submit'),
    
    path('<int:pk>/finalize/', views.finalize_invoice, name='finalize_invoice'),
    path('<int:pk>/pdf/', views.export_invoice_pdf, name='export_invoice_pdf'),
]
