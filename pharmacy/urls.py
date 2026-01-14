from django.urls import path
from . import views
from . import views_owner

app_name = 'pharmacy'

urlpatterns = [
    # Pharmacies
    path('', views.pharmacy_list, name='pharmacy_list'),
    path('pharmacy/<slug:slug>/', views.pharmacy_detail, name='pharmacy_detail'),
    
    # Medicines
    path('medicines/', views.medicine_list, name='medicine_list'),
    path('medicine/<slug:slug>/', views.medicine_detail, name='medicine_detail'),

    # Cart
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:medicine_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),

    # Orders
    path('orders/', views.order_list, name='order_list'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),
    path('orders/<str:order_number>/cancel/', views.cancel_order, name='cancel_order'),

    # Prescriptions
    path('prescriptions/', views.prescription_list, name='prescription_list'),
    path('prescriptions/upload/', views.prescription_upload, name='prescription_upload'),
    path('prescriptions/<int:pk>/', views.prescription_detail, name='prescription_detail'),

    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:medicine_id>/', views.toggle_wishlist, name='toggle_wishlist'),

    # ============================================
    # Pharmacy Owner CRUD URLs
    # ============================================
    # Medicine Management
    path('owner/medicines/', views_owner.medicine_list, name='owner_medicine_list'),
    path('owner/medicines/create/', views_owner.medicine_create, name='owner_medicine_create'),
    path('owner/medicines/<int:pk>/', views_owner.medicine_detail, name='owner_medicine_detail'),
    path('owner/medicines/<int:pk>/update/', views_owner.medicine_update, name='owner_medicine_update'),
    path('owner/medicines/<int:pk>/delete/', views_owner.medicine_delete, name='owner_medicine_delete'),
    path('owner/medicines/<int:pk>/toggle/', views_owner.medicine_toggle_active, name='owner_medicine_toggle'),
]
