"""
Rent PWA URLs - Standalone Progressive Web App routes
"""

from django.urls import path
from . import views

app_name = 'rent_pwa'

urlpatterns = [
    # PWA Dashboard
    path('', views.pwa_dashboard, name='dashboard'),

    # Browse Equipment
    path('equipment/', views.pwa_equipment_list, name='equipment_list'),
    path('equipment/<int:pk>/', views.pwa_equipment_detail, name='equipment_detail'),
    path('equipment/category/<str:category>/', views.pwa_category_equipment, name='category_equipment'),

    # Bookings
    path('book/equipment/<int:equipment_id>/', views.pwa_book_equipment, name='book_equipment'),
    path('bookings/', views.pwa_booking_list, name='booking_list'),
    path('bookings/<int:booking_id>/', views.pwa_booking_detail, name='booking_detail'),
    path('bookings/<int:booking_id>/cancel/', views.pwa_cancel_booking, name='cancel_booking'),

    # Saved/Favorites (Equipment only)
    path('saved/', views.pwa_saved_equipment, name='saved_equipment'),
    path('saved/toggle/<int:equipment_id>/', views.pwa_toggle_saved, name='toggle_saved'),

    # Search
    path('search/', views.pwa_search, name='search'),

    # Owner Section  
    path('manage/', views.pwa_owner_dashboard, name='owner_dashboard'),
    path('manage/equipment/', views.pwa_manage_equipment, name='manage_equipment'),
    path('manage/equipment/add/', views.pwa_add_equipment, name='add_equipment'),
    path('manage/equipment/<int:equipment_id>/edit/', views.pwa_edit_equipment, name='edit_equipment'),
    path('manage/bookings/', views.pwa_manage_bookings, name='manage_bookings'),
    path('manage/bookings/<int:booking_id>/', views.pwa_booking_detail_owner, name='booking_detail_owner'),
    path('manage/bookings/<int:booking_id>/update-status/', views.pwa_update_booking_status, name='update_booking_status'),
    path('manage/analytics/', views.pwa_analytics, name='analytics'),
    path('manage/settings/', views.pwa_settings, name='settings'),

    # Notifications
    path('notifications/', views.pwa_notifications, name='notifications'),
]
