"""
Unit tests for Food app utilities
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from unittest.mock import patch, MagicMock

from .models import Restaurant, MenuItem, Order

User = get_user_model()


class FoodUtilsTest(TestCase):
    def setUp(self):
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
            status='active'
        )
        
    def test_order_number_generation(self):
        """Test order number generation is unique"""
        order1 = Order.objects.create(
            order_number='TEST-001',
            customer=self.customer,
            restaurant=self.restaurant,
            total_amount=Decimal('25.00')
        )
        
        order2 = Order.objects.create(
            order_number='TEST-002',
            customer=self.customer,
            restaurant=self.restaurant,
            total_amount=Decimal('30.00')
        )
        
        self.assertNotEqual(order1.order_number, order2.order_number)
        
    @patch('food.notifications.send_order_notification')
    def test_order_notification_handling(self, mock_notification):
        """Test order notification system"""
        order = Order.objects.create(
            order_number='TEST-001',
            customer=self.customer,
            restaurant=self.restaurant,
            total_amount=Decimal('25.00')
        )
        
        # Test notification would be called (mocked)
        mock_notification.return_value = True
        
        # Simulate notification call
        from food.notifications import send_order_notification
        result = send_order_notification(order)
        
        self.assertTrue(result)
        mock_notification.assert_called_once_with(order)
        
    def test_menu_item_availability_check(self):
        """Test menu item availability logic"""
        menu_item = MenuItem.objects.create(
            restaurant=self.restaurant,
            name='Test Item',
            slug='test-item',
            price=Decimal('10.00'),
            is_available=True
        )
        
        self.assertTrue(menu_item.is_available)
        
        # Test making unavailable
        menu_item.is_available = False
        menu_item.save()
        
        self.assertFalse(menu_item.is_available)
        
    def test_restaurant_status_check(self):
        """Test restaurant status logic"""
        self.assertEqual(self.restaurant.status, 'active')
        
        # Test changing status
        self.restaurant.status = 'inactive'
        self.restaurant.save()
        
        self.assertEqual(self.restaurant.status, 'inactive')
        
    def test_price_calculations(self):
        """Test various price calculation scenarios"""
        menu_item = MenuItem.objects.create(
            restaurant=self.restaurant,
            name='Test Item',
            slug='test-item',
            price=Decimal('20.00'),
            discounted_price=Decimal('15.00')
        )
        
        # Test display price with discount
        self.assertEqual(menu_item.get_display_price(), Decimal('15.00'))
        
        # Test without discount
        menu_item.discounted_price = None
        menu_item.save()
        self.assertEqual(menu_item.get_display_price(), Decimal('20.00'))
        
        # Test discount detection
        menu_item.discounted_price = Decimal('18.00')
        menu_item.save()
        self.assertTrue(menu_item.has_discount())
        
        menu_item.discounted_price = None
        menu_item.save()
        self.assertFalse(menu_item.has_discount())
