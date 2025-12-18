"""
Rent PWA URLs - Standalone Progressive Web App routes
"""

from django.urls import path
from . import views

app_name = 'rent_pwa'

urlpatterns = [
    # PWA Dashboard
    path('', views.pwa_dashboard, name='dashboard'),

    # Browse Properties
    path('properties/', views.pwa_property_list, name='property_list'),
    path('properties/<int:pk>/', views.pwa_property_detail, name='property_detail'),
    path('properties/category/<str:category>/', views.pwa_category_properties, name='category_properties'),

    # Browse Equipment
    path('equipment/', views.pwa_equipment_list, name='equipment_list'),
    path('equipment/<int:pk>/', views.pwa_equipment_detail, name='equipment_detail'),
    path('equipment/category/<str:category>/', views.pwa_category_equipment, name='category_equipment'),

    # Bookings
    path('book/property/<int:property_id>/', views.pwa_book_property, name='book_property'),
    path('book/equipment/<int:equipment_id>/', views.pwa_book_equipment, name='book_equipment'),
    path('bookings/', views.pwa_booking_list, name='booking_list'),
    path('bookings/<int:booking_id>/', views.pwa_booking_detail, name='booking_detail'),
    path('bookings/<int:booking_id>/cancel/', views.pwa_cancel_booking, name='cancel_booking'),

    # Saved/Favorites
    path('saved/', views.pwa_saved_properties, name='saved_properties'),
    path('saved/toggle/<int:property_id>/', views.pwa_toggle_saved, name='toggle_saved'),

    # Search
    path('search/', views.pwa_search, name='search'),

    # Landlord/Owner Section
    path('manage/', views.pwa_owner_dashboard, name='owner_dashboard'),
    path('manage/properties/', views.pwa_manage_properties, name='manage_properties'),
    path('manage/properties/add/', views.pwa_add_property, name='add_property'),
    path('manage/properties/<int:property_id>/edit/', views.pwa_edit_property, name='edit_property'),
    path('manage/properties/<int:property_id>/toggle/', views.pwa_toggle_property, name='toggle_property'),
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
