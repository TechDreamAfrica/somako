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
]