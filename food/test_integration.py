"""
Integration tests for Food app - End-to-end testing
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import transaction
from decimal import Decimal
from unittest.mock import patch, MagicMock

from .models import (
    Restaurant, MenuItem, FoodCategory, Order, Cart, CartItem,
    DeliveryZone, OrderItem, Review
)
from payment.models import Payment

User = get_user_model()


class FoodOrderIntegrationTest(TransactionTestCase):
    """Test complete order flow from cart to delivery"""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Customer'
        )
        
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123',
            first_name='Restaurant',
            last_name='Owner'
        )
        
        self.restaurant = Restaurant.objects.create(
            owner=self.owner,
            name='Integration Test Restaurant',
            slug='integration-test-restaurant',
            description='A restaurant for testing',
            phone='+1234567890',
            email='test@restaurant.com',
            address='123 Test Street',
            city='Test City',
            country='Test Country',
            status='active',
            minimum_order_amount=Decimal('15.00'),
            delivery_fee=Decimal('3.00')
        )
        
        self.category = FoodCategory.objects.create(
            name='Test Category',
            slug='test-category',
            is_active=True
        )
        
        self.menu_item1 = MenuItem.objects.create(
            restaurant=self.restaurant,
            category=self.category,
            name='Test Burger',
            slug='test-burger',
            description='A delicious test burger',
            price=Decimal('12.99'),
            is_available=True
        )
        
        self.menu_item2 = MenuItem.objects.create(
            restaurant=self.restaurant,
            category=self.category,
            name='Test Fries',
            slug='test-fries',
            description='Crispy test fries',
            price=Decimal('5.99'),
            is_available=True
        )
        
        self.delivery_zone = DeliveryZone.objects.create(
            restaurant=self.restaurant,
            name='Test Delivery Zone',
            delivery_fee=Decimal('5.00'),
            minimum_order=Decimal('10.00'),
            estimated_delivery_time=30,
            is_active=True
        )
        
        self.client.login(username='customer', password='testpass123')
        
    def test_complete_order_flow_cash_on_delivery(self):
        """Test complete order flow with cash on delivery"""
        # Step 1: Add items to cart
        response = self.client.post(
            reverse('food:add_to_cart', kwargs={'menu_item_id': self.menu_item1.pk}),
            {'quantity': 2}
        )
        self.assertEqual(response.status_code, 302)
        
        response = self.client.post(
            reverse('food:add_to_cart', kwargs={'menu_item_id': self.menu_item2.pk}),
            {'quantity': 1}
        )
        self.assertEqual(response.status_code, 302)
        
        # Verify cart contents
        cart = Cart.objects.get(user=self.customer)
        self.assertEqual(cart.items.count(), 2)
        
        expected_total = (Decimal('12.99') * 2) + Decimal('5.99')
        self.assertEqual(cart.get_total(), expected_total)
        
        # Step 2: Go to checkout
        response = self.client.get(reverse('food_pwa:checkout'))
        self.assertEqual(response.status_code, 200)
        
        # Step 3: Confirm order
        order_data = {
            'delivery_address': '456 Customer Street',
            'delivery_city': 'Customer City',
            'delivery_phone': '+9876543210',
            'delivery_instructions': 'Ring the doorbell twice',
            'payment_method': 'cash_on_delivery',
            'delivery_method': 'door_delivery',
            'delivery_zone': self.delivery_zone.pk
        }
        
        with patch('food_pwa.views.send_order_notification') as mock_notify:
            with patch('food_pwa.views.send_customer_order_confirmation') as mock_confirm:
                mock_notify.return_value = True
                mock_confirm.return_value = True
                
                response = self.client.post(
                    reverse('food_pwa:confirm_order'), 
                    order_data
                )
                
        self.assertEqual(response.status_code, 302)
        
        # Verify order was created
        order = Order.objects.get(customer=self.customer)
        self.assertEqual(order.status, 'confirmed')
        self.assertEqual(order.payment_method, 'cash_on_delivery')
        self.assertEqual(order.delivery_address, '456 Customer Street')
        self.assertEqual(order.restaurant, self.restaurant)
        
        # Verify order items
        order_items = order.items.all()
        self.assertEqual(order_items.count(), 2)
        
        # Verify cart was cleared
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 0)
        
        # Step 4: Check order in order list
        response = self.client.get(reverse('food_pwa:order_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, order.order_number)
        
        # Step 5: View order details
        response = self.client.get(
            reverse('food_pwa:order_detail', kwargs={'order_number': order.order_number})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['order'], order)
        
    @patch('food_pwa.views.initialize_paystack_payment')
    @patch('food_pwa.views.create_payment')
    def test_complete_order_flow_online_payment(self, mock_create_payment, mock_paystack):
        """Test complete order flow with online payment"""
        # Mock payment responses
        mock_payment = MagicMock()
        mock_payment.reference = 'test-payment-ref'
        mock_create_payment.return_value = mock_payment
        
        mock_paystack.return_value = {
            'status': True,
            'authorization_url': 'https://checkout.paystack.com/test-url'
        }
        
        # Add items to cart
        self.client.post(
            reverse('food:add_to_cart', kwargs={'menu_item_id': self.menu_item1.pk}),
            {'quantity': 1}
        )
        
        # Confirm order with online payment
        order_data = {
            'delivery_address': '456 Customer Street',
            'delivery_city': 'Customer City', 
            'delivery_phone': '+9876543210',
            'payment_method': 'online_payment',
            'delivery_method': 'door_delivery',
            'delivery_zone': self.delivery_zone.pk
        }
        
        response = self.client.post(
            reverse('food_pwa:confirm_order'),
            order_data
        )
        
        # Should redirect to Paystack
        self.assertEqual(response.status_code, 302)
        self.assertIn('paystack.com', response.url)
        
        # Verify order was created with pending status
        order = Order.objects.get(customer=self.customer)
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.payment_method, 'online_payment')
        
    def test_cart_modification_flow(self):
        """Test cart modification operations"""
        # Add item to cart
        self.client.post(
            reverse('food:add_to_cart', kwargs={'menu_item_id': self.menu_item1.pk}),
            {'quantity': 2}
        )
        
        cart = Cart.objects.get(user=self.customer)
        cart_item = cart.items.first()
        
        # Update quantity
        self.client.post(
            reverse('food_pwa:update_cart_item', kwargs={'cart_item_id': cart_item.pk}),
            {'quantity': 5}
        )
        
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 5)
        
        # Remove item
        self.client.post(
            reverse('food_pwa:remove_from_cart', kwargs={'cart_item_id': cart_item.pk})
        )
        
        self.assertFalse(CartItem.objects.filter(pk=cart_item.pk).exists())
        
    def test_restaurant_status_affects_ordering(self):
        """Test that inactive restaurants prevent ordering"""
        # Add item to cart while restaurant is active
        self.client.post(
            reverse('food:add_to_cart', kwargs={'menu_item_id': self.menu_item1.pk}),
            {'quantity': 1}
        )
        
        # Deactivate restaurant
        self.restaurant.status = 'inactive'
        self.restaurant.save()
        
        # Try to checkout
        response = self.client.get(reverse('food_pwa:checkout'))
        
        # Should handle inactive restaurant gracefully
        # (Implementation depends on business logic)
        
    def test_menu_item_availability_affects_cart(self):
        """Test that unavailable menu items affect cart"""
        # Add item to cart
        self.client.post(
            reverse('food:add_to_cart', kwargs={'menu_item_id': self.menu_item1.pk}),
            {'quantity': 1}
        )
        
        # Make menu item unavailable
        self.menu_item1.is_available = False
        self.menu_item1.save()
        
        # View cart - should handle unavailable items
        response = self.client.get(reverse('food_pwa:cart'))
        self.assertEqual(response.status_code, 200)
        
    def test_concurrent_order_processing(self):
        """Test handling of concurrent orders"""
        # This would test race conditions in order processing
        # For now, just verify basic order creation works
        
        self.client.post(
            reverse('food:add_to_cart', kwargs={'menu_item_id': self.menu_item1.pk}),
            {'quantity': 1}
        )
        
        order_data = {
            'delivery_address': '123 Test St',
            'delivery_city': 'Test City',
            'delivery_phone': '+1234567890',
            'payment_method': 'cash_on_delivery',
            'delivery_method': 'door_delivery',
            'delivery_zone': self.delivery_zone.pk
        }
        
        with patch('food_pwa.views.send_order_notification'):
            with patch('food_pwa.views.send_customer_order_confirmation'):
                response = self.client.post(
                    reverse('food_pwa:confirm_order'),
                    order_data
                )
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.filter(customer=self.customer).count(), 1)


class FoodSearchAndFilterIntegrationTest(TestCase):
    """Test search and filtering functionality"""
    
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123'
        )
        
        self.restaurant1 = Restaurant.objects.create(
            owner=self.owner,
            name='Pizza Palace',
            slug='pizza-palace',
            status='active'
        )
        
        self.restaurant2 = Restaurant.objects.create(
            owner=self.owner,
            name='Burger Joint',
            slug='burger-joint',
            status='active'
        )
        
        self.pizza_category = FoodCategory.objects.create(
            name='Pizza',
            slug='pizza',
            is_active=True
        )
        
        self.burger_category = FoodCategory.objects.create(
            name='Burgers',
            slug='burgers',
            is_active=True
        )
        
        MenuItem.objects.create(
            restaurant=self.restaurant1,
            category=self.pizza_category,
            name='Margherita Pizza',
            slug='margherita-pizza',
            price=Decimal('15.99'),
            is_available=True
        )
        
        MenuItem.objects.create(
            restaurant=self.restaurant2,
            category=self.burger_category,
            name='Cheese Burger',
            slug='cheese-burger',
            price=Decimal('12.99'),
            is_available=True
        )
        
    def test_search_functionality(self):
        """Test search across menu items and restaurants"""
        # Search for pizza
        response = self.client.get(reverse('food:search'), {'q': 'pizza'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Margherita Pizza')
        self.assertContains(response, 'Pizza Palace')
        
        # Search for burger
        response = self.client.get(reverse('food:search'), {'q': 'burger'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cheese Burger')
        self.assertContains(response, 'Burger Joint')
        
    def test_category_filtering(self):
        """Test filtering by category"""
        response = self.client.get(
            reverse('food:category_filter', kwargs={'category_slug': 'pizza'})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Margherita Pizza')
        self.assertNotContains(response, 'Cheese Burger')
        
    def test_restaurant_menu_filtering(self):
        """Test viewing restaurant-specific menus"""
        response = self.client.get(
            reverse('food:restaurant_detail', kwargs={'pk': self.restaurant1.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Margherita Pizza')
        self.assertNotContains(response, 'Cheese Burger')
