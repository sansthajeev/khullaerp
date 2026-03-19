from django.urls import path
from . import views

app_name = 'taxation'

urlpatterns = [
    path('tds-journal/', views.tds_journal_list, name='tds_journal_list'),
    path('tds-journal/new/', views.tds_journal_create, name='tds_journal_create'),
    path('tds-journal/<int:pk>/', views.tds_journal_detail, name='tds_journal_detail'),
    path('tds-journal/<int:pk>/edit/', views.tds_journal_edit, name='tds_journal_edit'),
    path('tds-journal/<int:pk>/delete/', views.tds_journal_delete, name='tds_journal_delete'),

    # TDS Headings (Revenue Codes)
    path('headings/', views.tds_heading_list, name='tds_heading_list'),
    path('headings/new/', views.tds_heading_create, name='tds_heading_create'),
    path('headings/load-defaults/', views.tds_headings_load_defaults, name='tds_headings_load_defaults'),
    path('headings/bulk-delete/', views.tds_heading_bulk_delete, name='tds_heading_bulk_delete'),
    path('headings/<int:pk>/edit/', views.tds_heading_edit, name='tds_heading_edit'),
    path('headings/<int:pk>/delete/', views.tds_heading_delete, name='tds_heading_delete'),
]
