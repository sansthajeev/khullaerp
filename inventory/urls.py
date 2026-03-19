from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('items/', views.item_list, name='item_list'),
    path('items/<int:pk>/', views.item_detail, name='item_detail'),
    path('items/bulk-generate-barcodes/', views.item_bulk_generate_barcodes, name='item_bulk_generate_barcodes'),
    path('items/create/', views.item_create, name='item_create'),
    path('items/<int:pk>/edit/', views.item_edit, name='item_edit'),
    path('items/<int:pk>/delete/', views.item_delete, name='item_delete'),
    path('items/<int:item_id>/ledger/', views.stock_ledger, name='item_ledger'),
    
    # Adjustments
    path('adjustments/', views.adjustment_list, name='adjustment_list'),
    path('adjustments/create/', views.adjustment_create, name='adjustment_create'),
    path('adjustments/<int:pk>/delete/', views.adjustment_delete, name='adjustment_delete'),
    
    # Reports
    path('reports/stock-report/', views.stock_report, name='stock_report'),
]
