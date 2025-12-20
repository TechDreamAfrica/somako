from django.urls import path
from . import views
from . import views_driver

app_name = 'ride'

urlpatterns = [
    # Ride Booking
    path('', views.ride_home, name='home'),
    path('book/', views.book_ride, name='book_ride'),
    path('ride/<uuid:ride_id>/', views.ride_detail, name='ride_detail'),
    path('ride/<uuid:ride_id>/track/', views.track_ride, name='track_ride'),
    path('ride/<uuid:ride_id>/cancel/', views.cancel_ride, name='cancel_ride'),
    path('ride/<uuid:ride_id>/rate/', views.rate_ride, name='rate_ride'),

    # Driver
    path('driver/dashboard/', views.driver_dashboard, name='driver_dashboard'),
    path('driver/rides/', views.driver_rides, name='driver_rides'),
    path('driver/available-rides/', views.available_rides, name='available_rides'),
    path('driver/toggle-availability/', views.toggle_driver_availability, name='toggle_availability'),
    path('driver/earnings/', views.driver_earnings, name='driver_earnings'),
    path('driver/profile/edit/', views.driver_profile_edit, name='driver_profile_edit'),
    path('driver/ride/<uuid:ride_id>/accept/', views.accept_ride, name='accept_ride'),
    path('driver/ride/<uuid:ride_id>/arrived/', views.driver_arrived, name='driver_arrived'),
    path('driver/ride/<uuid:ride_id>/start/', views.start_ride, name='start_ride'),
    path('driver/ride/<uuid:ride_id>/complete/', views.complete_ride, name='complete_ride'),

    # History
    path('history/', views.ride_history, name='ride_history'),

    # Payment
    path('payment/cash/<uuid:ride_id>/', views.confirm_cash_payment, name='confirm_cash_payment'),
    path('payment/initiate/<uuid:ride_id>/', views.initiate_payment, name='initiate_payment'),
    path('payment/verify/<uuid:ride_id>/', views.verify_payment, name='verify_payment'),

    # ============================================
    # Driver CRUD URLs
    # ============================================
    # Vehicle Management
    path('driver/vehicles/', views_driver.vehicle_list, name='driver_vehicle_list'),
    path('driver/vehicles/create/', views_driver.vehicle_create, name='driver_vehicle_create'),
    path('driver/vehicles/<int:pk>/', views_driver.vehicle_detail, name='driver_vehicle_detail'),
    path('driver/vehicles/<int:pk>/update/', views_driver.vehicle_update, name='driver_vehicle_update'),
    path('driver/vehicles/<int:pk>/delete/', views_driver.vehicle_delete, name='driver_vehicle_delete'),
    path('driver/vehicles/<int:pk>/toggle/', views_driver.vehicle_toggle_active, name='driver_vehicle_toggle'),
    path('driver/vehicles/<int:pk>/set-primary/', views_driver.vehicle_set_primary, name='driver_vehicle_set_primary'),
]
