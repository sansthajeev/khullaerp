from django.urls import path
from . import views

app_name = 'accounting'
urlpatterns = [
    path('chart-of-accounts/', views.coa_list, name='coa_list'),
    path('vouchers/', views.voucher_list, name='voucher_list'),
    path('vouchers/create/', views.voucher_create, name='voucher_create'),
    path('vouchers/<int:pk>/', views.voucher_detail, name='voucher_detail'),
    path('vouchers/<int:pk>/edit/', views.voucher_edit, name='voucher_edit'),
    path('vouchers/<int:pk>/delete/', views.voucher_delete, name='voucher_delete'),
    path('vouchers/<int:pk>/export-pdf/', views.export_voucher_pdf, name='export_voucher_pdf'),
    
    # Reports
    path('reports/trial-balance/', views.trial_balance, name='trial_balance'),
    path('reports/profit-loss/', views.profit_loss, name='profit_loss'),
    path('reports/balance-sheet/', views.balance_sheet, name='balance_sheet'),
    path('reports/cash-flow/', views.cash_flow, name='cash_flow'),
    
    # VAT Reports
    path('reports/sales-vat/', views.sales_vat_report, name='sales_vat_report'),
    path('reports/purchase-vat/', views.purchase_vat_report, name='purchase_vat_report'),
    path('reports/sales-register/', views.sales_register, name='sales_register'),
    path('reports/purchase-register/', views.purchase_register, name='purchase_register'),
    path('reports/tds/', views.tds_report, name='tds_report'),
    path('ledger/<int:pk>/edit-basic/', views.ledger_edit_basic, name='ledger_edit_basic'),
    
    # Ledger Statement
    path('ledger-statement/', views.ledger_statement, name='ledger_statement'),
    path('ledger-statement/<int:ledger_id>/', views.ledger_statement, name='ledger_statement_detail'),
]
