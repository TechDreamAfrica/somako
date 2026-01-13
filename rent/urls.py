from django.urls import path
from django.http import HttpResponseRedirect
from django.urls import reverse
from . import views
from . import views_chat
from . import views_saved
from . import views_owner

app_name = 'rent'

# Helper function to redirect properties to equipment
def redirect_properties_to_equipment(request):
    return HttpResponseRedirect(reverse('rent:equipment_list'))

urlpatterns = [
    # PWA Dashboard
    path('dashboard/', views.dashboard_pwa, name='dashboard'),

    # Properties URLs now redirect to equipment
    path('properties/', redirect_properties_to_equipment, name='property_list'),
    
    # Equipment
    path('equipment/', views.equipment_list, name='equipment_list'),
    path('equipment/<int:pk>/', views.equipment_detail, name='equipment_detail'),
    path('my-equipment/', views.my_equipment, name='my_equipment'),

    # Bookings
    path('bookings/', views.booking_list, name='booking_list'),
    path('bookings/create/', views.booking_create, name='booking_create'),
    path('bookings/<int:pk>/', views.booking_detail, name='booking_detail'),
    path('bookings/<int:pk>/cancel/', views.booking_cancel, name='booking_cancel'),

    # Chat/Messaging
    path('chat/send/', views_chat.send_message, name='send_message'),
    path('chat/', views_chat.chat_thread, name='chat_thread'),
    path('messages/', views_chat.my_messages, name='my_messages'),

    # Saved/Favorites (only equipment now)
    path('equipment/<int:equipment_id>/save/', views_saved.toggle_save_equipment, name='toggle_save_equipment'),
    path('saved/', views_saved.saved_items, name='saved_items'),
    path('saved/equipment/', views_saved.saved_equipment, name='saved_equipment'),

    # ============================================
    # Equipment Owner CRUD URLs
    # ============================================
    path('owner/equipment/', views_owner.equipment_list, name='owner_equipment_list'),
    path('owner/equipment/create/', views_owner.equipment_create, name='owner_equipment_create'),
    path('owner/equipment/<int:pk>/', views_owner.equipment_detail, name='owner_equipment_detail'),
    path('owner/equipment/<int:pk>/update/', views_owner.equipment_update, name='owner_equipment_update'),
    path('owner/equipment/<int:pk>/delete/', views_owner.equipment_delete, name='owner_equipment_delete'),
    path('owner/equipment/<int:pk>/toggle/', views_owner.equipment_toggle_availability, name='owner_equipment_toggle'),
    
    # Equipment Owner Booking Management
    path('owner/bookings/', views_owner.booking_list, name='owner_booking_list'),
    path('owner/bookings/<int:pk>/', views_owner.booking_detail, name='owner_booking_detail'),
    path('owner/bookings/<int:pk>/update-status/', views_owner.booking_update_status, name='owner_booking_update_status'),
]