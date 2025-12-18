from django.urls import path
from . import views
from . import views_restaurant
from . import views_owner

app_name = 'food'

urlpatterns = [
    # Public - Restaurants
    path('', views.restaurant_list, name='restaurant_list'),
    path('restaurant/<slug:slug>/', views.restaurant_detail, name='restaurant_detail'),
    path('restaurant/<slug:slug>/menu/', views.restaurant_menu, name='restaurant_menu'),

    # Cart
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),

    # Customer Orders
    path('orders/', views.order_list, name='order_list'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),
    path('orders/<str:order_number>/track/', views.track_order, name='track_order'),

    # Restaurant Owner Dashboard
    path('dashboard/', views_restaurant.restaurant_dashboard, name='dashboard'),
    path('dashboard/pwa/', views_restaurant.restaurant_dashboard, name='dashboard_pwa'),

    # Restaurant Management
    path('manage/orders/', views_restaurant.manage_orders, name='manage_orders'),
    path('manage/orders/<int:order_id>/update-status/', views_restaurant.update_order_status, name='update_order_status'),
    path('manage/menu/', views_restaurant.manage_menu, name='manage_menu'),
    path('manage/menu/<int:item_id>/toggle-availability/', views_restaurant.toggle_menu_item_availability, name='toggle_menu_item_availability'),
    path('manage/analytics/', views_restaurant.restaurant_analytics, name='restaurant_analytics'),

    # ============================================
    # Restaurant Owner CRUD URLs
    # ============================================
    # Restaurant Management
    path('owner/restaurants/', views_owner.restaurant_list, name='owner_restaurant_list'),
    path('owner/restaurants/create/', views_owner.restaurant_create, name='owner_restaurant_create'),
    path('owner/restaurants/<int:pk>/', views_owner.restaurant_detail, name='owner_restaurant_detail'),
    path('owner/restaurants/<int:pk>/update/', views_owner.restaurant_update, name='owner_restaurant_update'),
    path('owner/restaurants/<int:pk>/delete/', views_owner.restaurant_delete, name='owner_restaurant_delete'),
    path('owner/restaurants/<int:pk>/toggle-status/', views_owner.restaurant_toggle_status, name='owner_restaurant_toggle_status'),

    # MenuItem Management
    path('owner/restaurants/<int:restaurant_pk>/menu/create/', views_owner.menu_item_create, name='owner_menu_item_create'),
    path('owner/menu/<int:pk>/update/', views_owner.menu_item_update, name='owner_menu_item_update'),
    path('owner/menu/<int:pk>/delete/', views_owner.menu_item_delete, name='owner_menu_item_delete'),
    path('owner/menu/<int:pk>/toggle/', views_owner.menu_item_toggle_availability, name='owner_menu_item_toggle'),
]
