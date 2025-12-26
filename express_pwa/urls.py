"""
Express PWA URLs - Standalone Progressive Web App routes for package delivery
"""

from django.urls import path
from . import views
from . import views_rider

app_name = 'express_pwa'

urlpatterns = [
    # PWA Dashboard
    path('', views.pwa_dashboard, name='dashboard'),

    # Order-based Delivery Management

    # Rider/Driver Registration & Profile
    path('rider/become-driver/', views_rider.become_delivery_driver, name='become_driver'),
    path('rider/profile/', views_rider.rider_profile, name='rider_profile'),

    # Rider Dashboard & Deliveries
    path('rider/', views_rider.rider_dashboard, name='rider_dashboard'),
    path('rider/available/', views_rider.available_deliveries, name='rider_available_deliveries'),
    path('rider/accept/<int:request_id>/', views_rider.accept_delivery, name='rider_accept_delivery'),
    path('rider/my-deliveries/', views_rider.my_deliveries, name='rider_my_deliveries'),
    path('rider/delivery/<int:delivery_id>/', views_rider.delivery_detail_rider, name='delivery_detail_rider'),
    path('rider/delivery/<int:delivery_id>/update-status/', views_rider.update_delivery_status_rider, name='update_delivery_status_rider'),
    
    # Rider Order Management
    path('rider/order/<int:order_id>/', views_rider.order_detail_rider, name='order_detail_rider'),
    path('rider/order/<int:order_id>/start/', views_rider.start_order, name='start_order'),
    path('rider/order/<int:order_id>/item/<int:item_id>/update-status/', views_rider.update_order_item_status, name='update_order_item_status'),

    # Rider Actions
    path('rider/toggle-availability/', views_rider.toggle_availability, name='toggle_availability'),
    path('rider/earnings/', views_rider.rider_earnings, name='rider_earnings'),
    path('rider/request-payout/', views_rider.request_payout, name='request_payout'),
    path('rider/delivery/<int:delivery_id>/signature/', views_rider.rider_capture_signature, name='rider_capture_signature'),

    # Legacy Driver Section (redirects to new rider system for backwards compatibility)
    path('driver/', views.pwa_driver_dashboard, name='driver_dashboard'),
    path('driver/available/', views.pwa_redirect_to_rider_available, name='available_deliveries'),
    path('driver/accept/<int:request_id>/', views.pwa_redirect_to_rider_accept, name='accept_delivery'),
    path('driver/my-deliveries/', views.pwa_redirect_to_rider_deliveries, name='my_deliveries'),
    path('driver/delivery/<int:delivery_id>/update-status/', views.pwa_redirect_to_rider_delivery, name='update_delivery_status'),
    path('driver/delivery/<int:delivery_id>/complete/', views.pwa_redirect_to_rider_delivery, name='complete_delivery'),
    path('driver/delivery/<int:delivery_id>/signature/', views.pwa_redirect_to_rider_signature, name='capture_signature'),

    # Search & Filters

    path('track/<str:tracking_number>/', views.pwa_track_by_number, name='track_by_number'),

    # Pricing & Estimates
    path('estimate/', views.pwa_delivery_estimate, name='delivery_estimate'),
    path('pricing/', views.pwa_pricing_info, name='pricing_info'),
    
    # AJAX endpoints
    path('ajax/areas-by-region/', views.pwa_get_areas_by_region, name='get_areas_by_region'),
    path('ajax/manual-assign-drivers/', views.pwa_manual_assign_drivers, name='manual_assign_drivers'),

    # History & Analytics  
    path('history/', views.pwa_delivery_history, name='delivery_history'),
    path('delivery-requests/', views.pwa_delivery_requests, name='delivery_requests'),
    path('analytics/', views.pwa_delivery_analytics, name='delivery_analytics'),

    # Notifications
    path('notifications/', views.pwa_notifications, name='notifications'),
    path('notifications/<int:notification_id>/mark-read/', views.pwa_mark_notification_read, name='mark_notification_read'),

    # Order Management System
    path('orders/', views.pwa_order_list, name='order_list'),
    path('orders/tracking/', views.pwa_order_tracking, name='order_tracking'),
    path('orders/create/', views.pwa_create_order, name='create_order'),
    path('orders/<str:order_number>/', views.pwa_order_detail, name='order_detail'),
    path('orders/<str:order_number>/edit/', views.pwa_edit_order, name='edit_order'),
    path('orders/<str:order_number>/add-item/', views.pwa_add_item, name='add_item'),
    path('orders/<str:order_number>/item/<int:item_id>/edit/', views.pwa_edit_item, name='edit_item'),
    path('orders/<str:order_number>/item/<int:item_id>/delete/', views.pwa_delete_item, name='delete_item'),
    path('orders/<str:order_number>/submit/', views.pwa_submit_order, name='submit_order'),
    path('orders/<str:order_number>/assign-driver/', views.pwa_assign_driver, name='assign_driver'),
    path('orders/<str:order_number>/update-status/', views.pwa_update_order_status, name='update_order_status'),
    path('orders/<str:order_number>/delete/', views.pwa_delete_order, name='delete_order'),
    
    # AJAX endpoints
    path('ajax/get-areas/', views.get_areas_by_region, name='get_areas_by_region'),

    # Rider Order Management
    path('rider/order/<int:order_id>/', views_rider.order_detail_rider, name='order_detail_rider'),
    path('rider/order/<int:order_id>/start/', views_rider.start_order, name='start_order'),
    path('rider/order/<int:order_id>/item/<int:item_id>/update/', views_rider.update_order_item_status, name='update_order_item_status'),
]