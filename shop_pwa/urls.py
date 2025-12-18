"""
Shop PWA URLs - Standalone Progressive Web App routes
"""

from django.urls import path
from . import views

app_name = 'shop_pwa'

urlpatterns = [
    # PWA Dashboard
    path('', views.pwa_dashboard, name='dashboard'),

    # Browse Products
    path('products/', views.pwa_product_list, name='product_list'),
    path('products/<int:pk>/', views.pwa_product_detail, name='product_detail'),
    path('categories/<str:category>/', views.pwa_category_products, name='category_products'),

    # Cart & Checkout
    path('cart/', views.pwa_cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.pwa_add_to_cart, name='add_to_cart'),
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

    # Search & Filters
    path('search/', views.pwa_search, name='search'),

    # Favorites
    path('favorites/', views.pwa_favorites, name='favorites'),
    path('favorites/toggle/<int:product_id>/', views.pwa_toggle_favorite, name='toggle_favorite'),

    # Shop Owner Section
    path('manage/', views.pwa_owner_dashboard, name='owner_dashboard'),
    path('manage/orders/', views.pwa_manage_orders, name='manage_orders'),
    path('manage/orders/<int:order_id>/', views.pwa_order_detail_owner, name='order_detail_owner'),
    path('manage/orders/<int:order_id>/update-status/', views.pwa_update_order_status, name='update_order_status'),
    path('manage/products/', views.pwa_manage_products, name='manage_products'),
    path('manage/products/add/', views.pwa_add_product, name='add_product'),
    path('manage/products/<int:product_id>/edit/', views.pwa_edit_product, name='edit_product'),
    path('manage/products/<int:product_id>/toggle/', views.pwa_toggle_product, name='toggle_product'),
    path('manage/products/<int:product_id>/delete/', views.pwa_delete_product, name='delete_product'),
    path('manage/analytics/', views.pwa_analytics, name='analytics'),
    path('manage/settings/', views.pwa_shop_settings, name='shop_settings'),

    # Notifications
    path('notifications/', views.pwa_notifications, name='notifications'),
]
