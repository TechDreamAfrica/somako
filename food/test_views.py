"""
Unit tests for Food app views
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal

from .models import Restaurant, MenuItem, FoodCategory, Order, Cart, CartItem

User = get_user_model()


class FoodViewsTest(TestCase):
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
            status='active'
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
        
    def test_restaurant_list_view(self):
        """Test restaurant list page"""
        response = self.client.get(reverse('food:restaurant_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Restaurant')
        self.assertIn('restaurants', response.context)
        
    def test_restaurant_detail_view(self):
        """Test restaurant detail page"""
        response = self.client.get(
            reverse('food:restaurant_detail', kwargs={'pk': self.restaurant.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Restaurant')
        self.assertContains(response, 'Test Pizza')
        self.assertEqual(response.context['restaurant'], self.restaurant)
        
    def test_menu_item_detail_view(self):
        """Test menu item detail page"""
        response = self.client.get(
            reverse('food:menu_item_detail', kwargs={'pk': self.menu_item.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Pizza')
        self.assertEqual(response.context['menu_item'], self.menu_item)
        
    def test_cart_view_requires_login(self):
        """Test cart view requires authentication"""
        response = self.client.get(reverse('food:cart_view'))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        
    def test_cart_view_authenticated(self):
        """Test cart view when authenticated"""
        self.client.login(username='customer', password='testpass123')
        
        response = self.client.get(reverse('food:cart_view'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('cart_items', response.context)
        
    def test_add_to_cart_requires_login(self):
        """Test add to cart requires authentication"""
        response = self.client.post(
            reverse('food:add_to_cart', kwargs={'menu_item_id': self.menu_item.pk}),
            {'quantity': 1}
        )
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        
    def test_add_to_cart_authenticated(self):
        """Test adding item to cart when authenticated"""
        self.client.login(username='customer', password='testpass123')
        
        response = self.client.post(
            reverse('food:add_to_cart', kwargs={'menu_item_id': self.menu_item.pk}),
            {'quantity': 2}
        )
        
        # Should redirect (success)
        self.assertEqual(response.status_code, 302)
        
        # Check cart item was created
        cart = Cart.objects.get(user=self.customer)
        cart_items = cart.items.all()
        
        self.assertEqual(cart_items.count(), 1)
        self.assertEqual(cart_items.first().quantity, 2)
        self.assertEqual(cart_items.first().menu_item, self.menu_item)
        
    def test_order_list_requires_login(self):
        """Test order list requires authentication"""
        response = self.client.get(reverse('food:order_list'))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        
    def test_order_list_authenticated(self):
        """Test order list when authenticated"""
        self.client.login(username='customer', password='testpass123')
        
        # Create a test order
        order = Order.objects.create(
            order_number='TEST-001',
            customer=self.customer,
            restaurant=self.restaurant,
            total_amount=Decimal('25.00'),
            status='pending'
        )
        
        response = self.client.get(reverse('food:order_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TEST-001')
        self.assertIn('orders', response.context)
        
    def test_order_detail_view(self):
        """Test order detail page"""
        self.client.login(username='customer', password='testpass123')
        
        order = Order.objects.create(
            order_number='TEST-001',
            customer=self.customer,
            restaurant=self.restaurant,
            total_amount=Decimal('25.00'),
            status='pending'
        )
        
        response = self.client.get(
            reverse('food:order_detail', kwargs={'order_number': order.order_number})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['order'], order)
        
    def test_search_view(self):
        """Test search functionality"""
        response = self.client.get(reverse('food:search'), {'q': 'pizza'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Pizza')
        
    def test_category_filter_view(self):
        """Test category filter"""
        response = self.client.get(
            reverse('food:category_filter', kwargs={'category_slug': 'pizza'})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Pizza')
        
    def test_invalid_restaurant_returns_404(self):
        """Test accessing non-existent restaurant returns 404"""
        response = self.client.get(
            reverse('food:restaurant_detail', kwargs={'pk': 99999})
        )
        
        self.assertEqual(response.status_code, 404)
        
    def test_invalid_menu_item_returns_404(self):
        """Test accessing non-existent menu item returns 404"""
        response = self.client.get(
            reverse('food:menu_item_detail', kwargs={'pk': 99999})
        )
        
        self.assertEqual(response.status_code, 404)
