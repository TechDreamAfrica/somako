from django.urls import path
from . import views
from . import views_seller

app_name = 'shop'

urlpatterns = [
    # Shops
    path('', views.shop_list, name='shop_list'),
    path('shop/<slug:slug>/', views.shop_detail, name='shop_detail'),

    # Products
    path('products/', views.product_list, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('category/<slug:slug>/', views.category_products, name='category_products'),

    # Cart
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:variant_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('payment/verify/<str:reference>/', views.payment_verify, name='payment_verify'),

    # Orders
    path('orders/', views.order_list, name='order_list'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),

    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),

    # ============================================
    # Seller CRUD URLs
    # ============================================
    # Product Management
    path('seller/products/', views_seller.product_list, name='seller_product_list'),
    path('seller/products/create/', views_seller.product_create, name='seller_product_create'),
    path('seller/products/<int:pk>/', views_seller.product_detail, name='seller_product_detail'),
    path('seller/products/<int:pk>/update/', views_seller.product_update, name='seller_product_update'),
    path('seller/products/<int:pk>/delete/', views_seller.product_delete, name='seller_product_delete'),
    path('seller/products/<int:pk>/toggle/', views_seller.product_toggle_active, name='seller_product_toggle'),

    # Product Image Management
    path('seller/products/<int:product_pk>/images/add/', views_seller.product_image_add, name='seller_product_image_add'),
    path('seller/images/<int:pk>/delete/', views_seller.product_image_delete, name='seller_product_image_delete'),
]
