"""
Ride PWA URLs - Standalone Progressive Web App routes
"""

from django.urls import path
from . import views

app_name = 'ride_pwa'

urlpatterns = [
    # PWA Dashboard
    path('', views.pwa_dashboard, name='dashboard'),

    # Location Update
    path('update-location/', views.update_location, name='update_location'),

    # Rider Section (Book Rides)
    path('book/', views.pwa_book_ride, name='book_ride'),
    path('rides/', views.pwa_ride_list, name='ride_list'),
    path('rides/<int:ride_id>/', views.pwa_ride_detail, name='ride_detail'),
    path('rides/<int:ride_id>/track/', views.pwa_track_ride, name='track_ride'),
    path('rides/<int:ride_id>/cancel/', views.pwa_cancel_ride, name='cancel_ride'),
    path('rides/<int:ride_id>/complete/', views.pwa_complete_ride_passenger, name='complete_ride'),
    path('rides/<int:ride_id>/rate/', views.pwa_rate_ride, name='rate_ride'),

    # Search
    path('search/', views.pwa_search, name='search'),

    # Driver Section
    path('driver/', views.pwa_driver_dashboard, name='driver_dashboard'),
    path('driver/available-rides/', views.pwa_available_rides, name='available_rides'),
    path('driver/accept/<int:ride_id>/', views.pwa_accept_ride, name='accept_ride'),
    path('driver/reject/<int:ride_id>/', views.pwa_reject_ride, name='reject_ride'),
    path('driver/active/', views.pwa_active_rides, name='active_rides'),
    path('driver/rides/<int:ride_id>/', views.pwa_driver_ride_detail, name='driver_ride_detail'),
    path('driver/rides/<int:ride_id>/update-status/', views.pwa_update_ride_status, name='update_ride_status'),
    path('driver/earnings/', views.pwa_driver_earnings, name='driver_earnings'),
    path('driver/profile/', views.pwa_driver_profile, name='driver_profile'),
    path('driver/analytics/', views.pwa_driver_analytics, name='driver_analytics'),
    path('driver/toggle-availability/', views.pwa_toggle_availability, name='toggle_availability'),

    # Notifications
    path('notifications/', views.pwa_notifications, name='notifications'),
]
