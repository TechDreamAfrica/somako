"""
Unit tests for Food app models
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone

from .models import (
    Restaurant, OperatingHours, FoodCategory, MenuItem,
    AddonCategory, Addon, DeliveryZone, Cart, CartItem,
    Order, OrderItem, OrderItemAddon, Review, Wishlist, WishlistItem
)

User = get_user_model()


class RestaurantModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testowner',
            email='owner@test.com',
            password='testpass123'
        )
        
    def test_create_restaurant(self):
        restaurant = Restaurant.objects.create(
            owner=self.user,
            name='Test Restaurant',
            slug='test-restaurant',
            description='A test restaurant',
            phone='+1234567890',
            email='test@restaurant.com',
            address='123 Test St',
            city='Test City',
            country='Test Country',
            status='active'
        )
        
        self.assertEqual(restaurant.name, 'Test Restaurant')
        self.assertEqual(restaurant.owner, self.user)
        self.assertEqual(restaurant.status, 'active')
        self.assertEqual(str(restaurant), 'Test Restaurant')
        
    def test_restaurant_slug_unique(self):
        Restaurant.objects.create(
            owner=self.user,
            name='Test Restaurant',
            slug='test-restaurant',
            status='active'
        )
        
        with self.assertRaises(Exception):  # IntegrityError for unique constraint
            Restaurant.objects.create(
                owner=self.user,
                name='Another Restaurant',
                slug='test-restaurant',
                status='active'
            )
    
    def test_get_logo_url(self):
        restaurant = Restaurant.objects.create(
            owner=self.user,
            name='Test Restaurant',
            slug='test-restaurant'
        )
        
        # No logo
        self.assertIsNone(restaurant.get_logo_url())
        
    def test_get_image_url(self):
        restaurant = Restaurant.objects.create(
            owner=self.user,
            name='Test Restaurant',
            slug='test-restaurant'
        )
        
        # No image
        self.assertIsNone(restaurant.get_image_url())


class FoodCategoryModelTest(TestCase):
    def test_create_category(self):
        category = FoodCategory.objects.create(
            name='Pizza',
            slug='pizza',
            description='Delicious pizzas',
            is_active=True,
            display_order=1
        )
        
        self.assertEqual(category.name, 'Pizza')
        self.assertEqual(category.slug, 'pizza')
        self.assertTrue(category.is_active)
        self.assertEqual(str(category), 'Pizza')


class MenuItemModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testowner',
            email='owner@test.com',
            password='testpass123'
        )
        
        self.restaurant = Restaurant.objects.create(
            owner=self.user,
            name='Test Restaurant',
            slug='test-restaurant',
            status='active'
        )
        
        self.category = FoodCategory.objects.create(
            name='Pizza',
            slug='pizza'
        )
        
    def test_create_menu_item(self):
        menu_item = MenuItem.objects.create(
            restaurant=self.restaurant,
            category=self.category,
            name='Margherita Pizza',
            slug='margherita-pizza',
            description='Classic margherita pizza',
            price=Decimal('15.99'),
            is_available=True
        )
        
        self.assertEqual(menu_item.name, 'Margherita Pizza')
        self.assertEqual(menu_item.restaurant, self.restaurant)
        self.assertEqual(menu_item.category, self.category)
        self.assertEqual(menu_item.price, Decimal('15.99'))
        self.assertTrue(menu_item.is_available)
        self.assertEqual(str(menu_item), 'Test Restaurant - Margherita Pizza')
        
    def test_get_display_price(self):
        menu_item = MenuItem.objects.create(
            restaurant=self.restaurant,
            name='Test Item',
            slug='test-item',
            price=Decimal('20.00'),
            discounted_price=Decimal('15.00')
        )
        
        # Should return discounted price
        self.assertEqual(menu_item.get_display_price(), Decimal('15.00'))
        
        # Remove discount
        menu_item.discounted_price = None
        menu_item.save()
        
        # Should return regular price
        self.assertEqual(menu_item.get_display_price(), Decimal('20.00'))
        
    def test_has_discount(self):
        menu_item = MenuItem.objects.create(
            restaurant=self.restaurant,
            name='Test Item',
            slug='test-item',
            price=Decimal('20.00'),
            discounted_price=Decimal('15.00')
        )
        
        self.assertTrue(menu_item.has_discount())
        
        menu_item.discounted_price = None
        menu_item.save()
        
        self.assertFalse(menu_item.has_discount())
        
    def test_get_image_url(self):
        menu_item = MenuItem.objects.create(
            restaurant=self.restaurant,
            name='Test Item',
            slug='test-item',
            price=Decimal('20.00')
        )
        
        # No image
        self.assertIsNone(menu_item.get_image_url())
        
        # Test with URL string
        menu_item.image = 'https://example.com/image.jpg'
        menu_item.save()
        
        self.assertEqual(menu_item.get_image_url(), 'https://example.com/image.jpg')


class CartModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123'
        )
        
        self.owner = User.objects.create_user(
            username='testowner',
            email='owner@test.com',
            password='testpass123'
        )
        
        self.restaurant = Restaurant.objects.create(
            owner=self.owner,
            name='Test Restaurant',
            slug='test-restaurant',
            status='active'
        )
        
        self.menu_item = MenuItem.objects.create(
            restaurant=self.restaurant,
            name='Test Item',
            slug='test-item',
            price=Decimal('10.00')
        )
        
    def test_create_cart(self):
        cart = Cart.objects.create(user=self.user)
        
        self.assertEqual(cart.user, self.user)
        self.assertEqual(str(cart), f'Cart for {self.user.username}')
        
    def test_cart_get_total(self):
        cart = Cart.objects.create(user=self.user)
        
        # Empty cart
        self.assertEqual(cart.get_total(), 0)
        
        # Add item to cart
        cart_item = CartItem.objects.create(
            cart=cart,
            menu_item=self.menu_item,
            quantity=2
        )
        
        self.assertEqual(cart.get_total(), Decimal('20.00'))
        
    def test_cart_get_item_count(self):
        cart = Cart.objects.create(user=self.user)
        
        # Empty cart
        self.assertEqual(cart.get_item_count(), 0)
        
        # Add item to cart
        CartItem.objects.create(
            cart=cart,
            menu_item=self.menu_item,
            quantity=3
        )
        
        self.assertEqual(cart.get_item_count(), 3)


class CartItemModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123'
        )
        
        self.owner = User.objects.create_user(
            username='testowner',
            email='owner@test.com',
            password='testpass123'
        )
        
        self.restaurant = Restaurant.objects.create(
            owner=self.owner,
            name='Test Restaurant',
            slug='test-restaurant',
            status='active'
        )
        
        self.menu_item = MenuItem.objects.create(
            restaurant=self.restaurant,
            name='Test Item',
            slug='test-item',
            price=Decimal('10.00')
        )
        
        self.cart = Cart.objects.create(user=self.user)
        
    def test_create_cart_item(self):
        cart_item = CartItem.objects.create(
            cart=self.cart,
            menu_item=self.menu_item,
            quantity=2
        )
        
        self.assertEqual(cart_item.cart, self.cart)
        self.assertEqual(cart_item.menu_item, self.menu_item)
        self.assertEqual(cart_item.quantity, 2)
        
    def test_get_subtotal(self):
        cart_item = CartItem.objects.create(
            cart=self.cart,
            menu_item=self.menu_item,
            quantity=2
        )
        
        self.assertEqual(cart_item.get_subtotal(), Decimal('20.00'))


class OrderModelTest(TestCase):
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
        
    def test_create_order(self):
        order = Order.objects.create(
            order_number='TEST-001',
            customer=self.customer,
            restaurant=self.restaurant,
            delivery_method='door_delivery',
            payment_method='cash_on_delivery',
            delivery_address='123 Test St',
            delivery_city='Test City',
            delivery_phone='+1234567890',
            subtotal=Decimal('25.00'),
            delivery_fee=Decimal('5.00'),
            tax=Decimal('0.00'),
            total_amount=Decimal('30.00'),
            status='pending'
        )
        
        self.assertEqual(order.order_number, 'TEST-001')
        self.assertEqual(order.customer, self.customer)
        self.assertEqual(order.restaurant, self.restaurant)
        self.assertEqual(order.total_amount, Decimal('30.00'))
        self.assertEqual(str(order), 'Order #TEST-001')
        
    def test_can_cancel(self):
        order = Order.objects.create(
            order_number='TEST-001',
            customer=self.customer,
            restaurant=self.restaurant,
            status='pending',
            total_amount=Decimal('30.00')
        )
        
        # Can cancel when pending
        self.assertTrue(order.can_cancel())
        
        # Cannot cancel when delivered
        order.status = 'delivered'
        order.save()
        self.assertFalse(order.can_cancel())
        
    def test_can_review(self):
        order = Order.objects.create(
            order_number='TEST-001',
            customer=self.customer,
            restaurant=self.restaurant,
            status='delivered',
            total_amount=Decimal('30.00')
        )
        
        # Can review when delivered and no review exists
        self.assertTrue(order.can_review())


class DeliveryZoneModelTest(TestCase):
    def setUp(self):
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
        
    def test_create_delivery_zone(self):
        zone = DeliveryZone.objects.create(
            restaurant=self.restaurant,
            name='Downtown',
            delivery_fee=Decimal('5.00'),
            minimum_order=Decimal('20.00'),
            estimated_delivery_time=30,
            is_active=True
        )
        
        self.assertEqual(zone.name, 'Downtown')
        self.assertEqual(zone.restaurant, self.restaurant)
        self.assertEqual(zone.delivery_fee, Decimal('5.00'))
        self.assertTrue(zone.is_active)
        self.assertEqual(str(zone), 'Downtown - Test Restaurant')
