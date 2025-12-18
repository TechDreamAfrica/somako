"""
Food PWA URLs - Standalone Progressive Web App routes
These routes are specifically designed for the Food PWA and provide
a complete mobile-first experience separate from the web interface.
"""

from django.urls import path
from . import views

app_name = 'food_pwa'

urlpatterns = [
    # PWA Dashboard
    path('', views.pwa_dashboard, name='dashboard'),

    # Browse Restaurants
    path('restaurants/', views.pwa_restaurant_list, name='restaurant_list'),
    path('restaurants/<int:pk>/', views.pwa_restaurant_detail, name='restaurant_detail'),
    path('restaurants/<int:pk>/menu/', views.pwa_restaurant_menu, name='restaurant_menu'),

    # Cart & Checkout
    path('cart/', views.pwa_cart_view, name='cart'),
    path('cart/add/<int:menu_item_id>/', views.pwa_add_to_cart, name='add_to_cart'),
    path('cart/update/<int:cart_item_id>/', views.pwa_update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:cart_item_id>/', views.pwa_remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', views.pwa_clear_cart, name='clear_cart'),
    path('checkout/', views.pwa_checkout, name='checkout'),
    path('checkout/confirm/', views.pwa_confirm_order, name='confirm_order'),

    # Orders
    path('orders/', views.pwa_order_list, name='order_list'),
    path('orders/<str:order_number>/', views.pwa_order_detail, name='order_detail'),
    path('orders/<str:order_number>/track/', views.pwa_track_order, name='track_order'),
    path('orders/<str:order_number>/cancel/', views.pwa_cancel_order, name='cancel_order'),
    path('orders/<str:order_number>/reorder/', views.pwa_reorder, name='reorder'),

    # Search & Filters
    path('search/', views.pwa_search, name='search'),
    path('categories/<str:category>/', views.pwa_category_filter, name='category_filter'),

    # Favorites
    path('favorites/', views.pwa_favorites, name='favorites'),
    path('favorites/toggle/<int:restaurant_id>/', views.pwa_toggle_favorite, name='toggle_favorite'),

    # Restaurant Owner Section
    path('manage/', views.pwa_owner_dashboard, name='owner_dashboard'),
    path('manage/orders/', views.pwa_manage_orders, name='manage_orders'),
    path('manage/orders/<int:order_id>/', views.pwa_order_detail_owner, name='order_detail_owner'),
    path('manage/orders/<int:order_id>/update-status/', views.pwa_update_order_status, name='update_order_status'),
    path('manage/menu/', views.pwa_manage_menu, name='manage_menu'),
    path('manage/menu/add/', views.pwa_add_menu_item, name='add_menu_item'),
    path('manage/menu/<int:item_id>/edit/', views.pwa_edit_menu_item, name='edit_menu_item'),
    path('manage/menu/<int:item_id>/toggle/', views.pwa_toggle_menu_item, name='toggle_menu_item'),
    path('manage/menu/<int:item_id>/delete/', views.pwa_delete_menu_item, name='delete_menu_item'),
    path('manage/analytics/', views.pwa_analytics, name='analytics'),
    path('manage/settings/', views.pwa_restaurant_settings, name='restaurant_settings'),

    # Notifications
    path('notifications/', views.pwa_notifications, name='notifications'),
    path('notifications/<int:notification_id>/mark-read/', views.pwa_mark_notification_read, name='mark_notification_read'),
]
