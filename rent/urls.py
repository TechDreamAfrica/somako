from django.urls import path
from . import views
from . import views_landlord
from . import views_chat
from . import views_saved

app_name = 'rent'

urlpatterns = [
    # PWA Dashboard
    path('dashboard/', views.dashboard_pwa, name='dashboard'),

    # Properties
    path('properties/', views.property_list, name='property_list'),
    path('properties/<int:pk>/', views.property_detail, name='property_detail'),
    path('my-properties/', views.my_properties, name='my_properties'),

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

    # Saved/Favorites
    path('property/<int:property_id>/save/', views_saved.toggle_save_property, name='toggle_save_property'),
    path('equipment/<int:equipment_id>/save/', views_saved.toggle_save_equipment, name='toggle_save_equipment'),
    path('saved/', views_saved.saved_items, name='saved_items'),
    path('saved/properties/', views_saved.saved_properties, name='saved_properties'),
    path('saved/equipment/', views_saved.saved_equipment, name='saved_equipment'),

    # ============================================
    # Landlord CRUD URLs
    # ============================================
    # Property Management
    path('landlord/properties/', views_landlord.property_list, name='landlord_property_list'),
    path('landlord/properties/create/', views_landlord.property_create, name='landlord_property_create'),
    path('landlord/properties/<int:pk>/', views_landlord.property_detail, name='landlord_property_detail'),
    path('landlord/properties/<int:pk>/update/', views_landlord.property_update, name='landlord_property_update'),
    path('landlord/properties/<int:pk>/delete/', views_landlord.property_delete, name='landlord_property_delete'),
    path('landlord/properties/<int:pk>/toggle/', views_landlord.property_toggle_availability, name='landlord_property_toggle'),

    # Room Management
    path('landlord/properties/<int:property_pk>/rooms/create/', views_landlord.room_create, name='landlord_room_create'),
    path('landlord/rooms/<int:pk>/update/', views_landlord.room_update, name='landlord_room_update'),
    path('landlord/rooms/<int:pk>/delete/', views_landlord.room_delete, name='landlord_room_delete'),
    path('landlord/rooms/<int:pk>/toggle/', views_landlord.room_toggle_availability, name='landlord_room_toggle'),

    # Property Image Management
    path('landlord/properties/<int:property_pk>/images/add/', views_landlord.property_image_add, name='landlord_property_image_add'),
    path('landlord/images/<int:pk>/delete/', views_landlord.property_image_delete, name='landlord_property_image_delete'),
]