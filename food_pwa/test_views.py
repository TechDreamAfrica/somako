"""
Unit tests for Food PWA views
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal
from unittest.mock import patch, MagicMock

from food.models import (
    Restaurant, MenuItem, FoodCategory, Order, Cart, CartItem, DeliveryZone
)

User = get_user_model()


class FoodPWAViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        self.customer = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='testpass123'
        )
        
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123'
        )
        
        self.restaurant = Restaurant.objects.create(
            owner=self.owner,
            name='Test Restaurant',
            slug='test-restaurant',
            description='A test restaurant',
            status='active',
            minimum_order_amount=Decimal('15.00')
        )
        
        self.category = FoodCategory.objects.create(
            name='Pizza',
            slug='pizza',
            is_active=True
        )
        
        self.menu_item = MenuItem.objects.create(
            restaurant=self.restaurant,
            category=self.category,
            name='Test Pizza',
            slug='test-pizza',
            description='A test pizza',
            price=Decimal('15.99'),
            is_available=True
        )
        
        self.delivery_zone = DeliveryZone.objects.create(
            restaurant=self.restaurant,
            name='Test Zone',
            delivery_fee=Decimal('5.00'),
            minimum_order=Decimal('10.00'),
            is_active=True
        )
        
    def test_pwa_dashboard_requires_login(self):
        """Test PWA dashboard requires authentication"""
        response = self.client.get(reverse('food_pwa:dashboard'))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        
    def test_pwa_dashboard_authenticated(self):
        """Test PWA dashboard when authenticated"""
        self.client.login(username='customer', password='testpass123')
        
        response = self.client.get(reverse('food_pwa:dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('restaurants', response.context)
        
    def test_pwa_restaurant_list(self):
        """Test PWA restaurant list"""
        self.client.login(username='customer', password='testpass123')
        
        response = self.client.get(reverse('food_pwa:restaurant_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Restaurant')
        
    def test_pwa_restaurant_detail(self):
        """Test PWA restaurant detail"""
        self.client.login(username='customer', password='testpass123')
        
        response = self.client.get(
            reverse('food_pwa:restaurant_detail', kwargs={'pk': self.restaurant.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['restaurant'], self.restaurant)
        
    def test_pwa_add_to_cart(self):
        """Test PWA add to cart functionality"""
        self.client.login(username='customer', password='testpass123')
        
        response = self.client.post(
            reverse('food_pwa:add_to_cart', kwargs={'menu_item_id': self.menu_item.pk}),
            {
                'quantity': 2,
                'special_instructions': 'Extra cheese'
            }
        )
        
        # Should redirect after successful addition
        self.assertEqual(response.status_code, 302)
        
        # Verify cart item was created
        cart = Cart.objects.get(user=self.customer)
        cart_items = cart.items.all()
        
        self.assertEqual(cart_items.count(), 1)
        self.assertEqual(cart_items.first().quantity, 2)
        self.assertEqual(cart_items.first().special_instructions, 'Extra cheese')
        
    def test_pwa_cart_view(self):
        """Test PWA cart view"""
        self.client.login(username='customer', password='testpass123')
        
        # Add item to cart first
        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(
            cart=cart,
            menu_item=self.menu_item,
            quantity=1
        )
        
        response = self.client.get(reverse('food_pwa:cart'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('cart_items', response.context)
        
    def test_pwa_checkout_view(self):
        """Test PWA checkout view"""
        self.client.login(username='customer', password='testpass123')
        
        # Add item to cart first
        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(
            cart=cart,
            menu_item=self.menu_item,
            quantity=1
        )
        
        response = self.client.get(reverse('food_pwa:checkout'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('cart_items', response.context)
        self.assertIn('restaurant', response.context)
        
    def test_pwa_checkout_empty_cart(self):
        """Test PWA checkout with empty cart redirects"""
        self.client.login(username='customer', password='testpass123')
        
        response = self.client.get(reverse('food_pwa:checkout'))
        
        # Should redirect when cart is empty
        self.assertEqual(response.status_code, 302)
        
    @patch('food_pwa.views.create_payment')
    @patch('food_pwa.views.initialize_paystack_payment')
    @patch('food_pwa.views.send_order_notification')
    @patch('food_pwa.views.send_customer_order_confirmation')
    def test_pwa_confirm_order_cash_on_delivery(self, mock_customer_sms, mock_owner_sms, mock_paystack, mock_payment):
        """Test PWA order confirmation with cash on delivery"""
        self.client.login(username='customer', password='testpass123')
        
        # Add item to cart
        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(
            cart=cart,
            menu_item=self.menu_item,
            quantity=1
        )
        
        order_data = {
            'delivery_address': '123 Test Street',
            'delivery_city': 'Test City',
            'delivery_phone': '+1234567890',
            'delivery_instructions': 'Ring doorbell',
            'payment_method': 'cash_on_delivery',
            'delivery_method': 'door_delivery',
            'delivery_zone': self.delivery_zone.pk
        }
        
        response = self.client.post(reverse('food_pwa:confirm_order'), order_data)
        
        # Should redirect after successful order creation
        self.assertEqual(response.status_code, 302)
        
        # Verify order was created
        orders = Order.objects.filter(customer=self.customer)
        self.assertEqual(orders.count(), 1)
        
        order = orders.first()
        self.assertEqual(order.status, 'confirmed')
        self.assertEqual(order.payment_method, 'cash_on_delivery')
        self.assertEqual(order.delivery_address, '123 Test Street')
        
        # Verify cart was cleared
        self.assertEqual(cart.items.count(), 0)
        
    @patch('food_pwa.views.create_payment')
    @patch('food_pwa.views.initialize_paystack_payment')
    def test_pwa_confirm_order_online_payment(self, mock_paystack, mock_payment):
        """Test PWA order confirmation with online payment"""
        self.client.login(username='customer', password='testpass123')
        
        # Mock payment initialization success
        mock_payment.return_value = MagicMock()
        mock_paystack.return_value = {
            'status': True,
            'authorization_url': 'https://paystack.com/pay/test'
        }
        
        # Add item to cart
        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(
            cart=cart,
            menu_item=self.menu_item,
            quantity=1
        )
        
        order_data = {
            'delivery_address': '123 Test Street',
            'delivery_city': 'Test City',
            'delivery_phone': '+1234567890',
            'payment_method': 'online_payment',
            'delivery_method': 'door_delivery',
            'delivery_zone': self.delivery_zone.pk
        }
        
        response = self.client.post(reverse('food_pwa:confirm_order'), order_data)
        
        # Should redirect to Paystack
        self.assertEqual(response.status_code, 302)
        self.assertIn('paystack.com', response.url)
        
        # Verify order was created
        orders = Order.objects.filter(customer=self.customer)
        self.assertEqual(orders.count(), 1)
        
        order = orders.first()
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.payment_method, 'online_payment')
        
    def test_pwa_confirm_order_validation_errors(self):
        """Test PWA order confirmation with validation errors"""
        self.client.login(username='customer', password='testpass123')
        
        # Add item to cart
        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(
            cart=cart,
            menu_item=self.menu_item,
            quantity=1
        )
        
        # Missing required fields
        order_data = {
            'payment_method': 'cash_on_delivery'
        }
        
        response = self.client.post(reverse('food_pwa:confirm_order'), order_data)
        
        # Should redirect back to checkout
        self.assertEqual(response.status_code, 302)
        
        # No order should be created
        self.assertEqual(Order.objects.filter(customer=self.customer).count(), 0)
        
    def test_pwa_order_list(self):
        """Test PWA order list"""
        self.client.login(username='customer', password='testpass123')
        
        # Create test order
        order = Order.objects.create(
            order_number='PWA-TEST-001',
            customer=self.customer,
            restaurant=self.restaurant,
            total_amount=Decimal('25.00'),
            status='pending'
        )
        
        response = self.client.get(reverse('food_pwa:order_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PWA-TEST-001')
        
    def test_pwa_order_detail(self):
        """Test PWA order detail"""
        self.client.login(username='customer', password='testpass123')
        
        order = Order.objects.create(
            order_number='PWA-TEST-001',
            customer=self.customer,
            restaurant=self.restaurant,
            total_amount=Decimal('25.00'),
            status='pending'
        )
        
        response = self.client.get(
            reverse('food_pwa:order_detail', kwargs={'order_number': order.order_number})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['order'], order)
        
    def test_pwa_update_cart_item(self):
        """Test PWA update cart item"""
        self.client.login(username='customer', password='testpass123')
        
        cart = Cart.objects.create(user=self.customer)
        cart_item = CartItem.objects.create(
            cart=cart,
            menu_item=self.menu_item,
            quantity=1
        )
        
        response = self.client.post(
            reverse('food_pwa:update_cart_item', kwargs={'cart_item_id': cart_item.pk}),
            {'quantity': 3}
        )
        
        # Should redirect after update
        self.assertEqual(response.status_code, 302)
        
        # Verify quantity was updated
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 3)
        
    def test_pwa_remove_from_cart(self):
        """Test PWA remove item from cart"""
        self.client.login(username='customer', password='testpass123')
        
        cart = Cart.objects.create(user=self.customer)
        cart_item = CartItem.objects.create(
            cart=cart,
            menu_item=self.menu_item,
            quantity=1
        )
        
        response = self.client.post(
            reverse('food_pwa:remove_from_cart', kwargs={'cart_item_id': cart_item.pk})
        )
        
        # Should redirect after removal
        self.assertEqual(response.status_code, 302)
        
        # Verify item was removed
        self.assertFalse(CartItem.objects.filter(pk=cart_item.pk).exists())
        
    def test_pwa_clear_cart(self):
        """Test PWA clear entire cart"""
        self.client.login(username='customer', password='testpass123')
        
        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(
            cart=cart,
            menu_item=self.menu_item,
            quantity=1
        )
        
        response = self.client.post(reverse('food_pwa:clear_cart'))
        
        # Should redirect after clearing
        self.assertEqual(response.status_code, 302)
        
        # Verify cart was cleared
        self.assertEqual(cart.items.count(), 0)
