from django.urls import path
from django.http import HttpResponseRedirect
from django.urls import reverse
from . import views
from . import views_chat
from . import views_saved

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
    # Equipment Management
    path('owner/equipment/', views.equipment_list_owner, name='owner_equipment_list'),
    path('owner/equipment/create/', views.equipment_create, name='owner_equipment_create'),
    path('owner/equipment/<int:pk>/', views.equipment_detail_owner, name='owner_equipment_detail'),
    path('owner/equipment/<int:pk>/update/', views.equipment_update, name='owner_equipment_update'),
    path('owner/equipment/<int:pk>/delete/', views.equipment_delete, name='owner_equipment_delete'),
    path('owner/equipment/<int:pk>/toggle/', views.equipment_toggle_availability, name='owner_equipment_toggle'),

    # Equipment Image Management
    path('owner/equipment/<int:pk>/images/add/', views.equipment_image_add, name='owner_equipment_image_add'),
    path('owner/equipment/<int:pk>/images/<int:image_id>/delete/', views.equipment_image_delete, name='owner_equipment_image_delete'),

    # Equipment Booking Management
    path('owner/bookings/', views.equipment_bookings, name='owner_equipment_bookings'),
    path('owner/bookings/<int:booking_id>/approve/', views.equipment_booking_approve, name='owner_equipment_booking_approve'),
    path('owner/bookings/<int:booking_id>/reject/', views.equipment_booking_reject, name='owner_equipment_booking_reject'),
]

    # Room Management
    path('landlord/properties/<int:property_pk>/rooms/create/', views_landlord.room_create, name='landlord_room_create'),
    path('landlord/rooms/<int:pk>/update/', views_landlord.room_update, name='landlord_room_update'),
    path('landlord/rooms/<int:pk>/delete/', views_landlord.room_delete, name='landlord_room_delete'),
    path('landlord/rooms/<int:pk>/toggle/', views_landlord.room_toggle_availability, name='landlord_room_toggle'),

    # Property Image Management
    path('landlord/properties/<int:property_pk>/images/add/', views_landlord.property_image_add, name='landlord_property_image_add'),
    path('landlord/images/<int:pk>/delete/', views_landlord.property_image_delete, name='landlord_property_image_delete'),
]