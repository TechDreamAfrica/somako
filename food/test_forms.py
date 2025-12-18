"""
Unit tests for Food app forms
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal

from .forms import RestaurantForm, MenuItemForm
from .models import Restaurant, FoodCategory

User = get_user_model()


class RestaurantFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testowner',
            email='owner@test.com',
            password='testpass123'
        )
        
    def test_valid_restaurant_form(self):
        """Test creating restaurant with valid data"""
        form_data = {
            'name': 'Test Restaurant',
            'description': 'A great restaurant',
            'phone': '+1234567890',
            'email': 'test@restaurant.com',
            'address': '123 Test Street',
            'city': 'Test City',
            'country': 'Test Country',
            'cuisine_type': 'Italian',
            'opening_hours': '9:00 AM - 10:00 PM',
            'delivery_radius': 5,
            'minimum_order_amount': '20.00',
            'delivery_fee': '3.00',
            'estimated_delivery_time': 30,
            'is_featured': False,
            'status': 'active'
        }
        
        form = RestaurantForm(data=form_data)
        self.assertTrue(form.is_valid())
        
    def test_restaurant_form_missing_required_fields(self):
        """Test restaurant form with missing required fields"""
        form_data = {
            'description': 'A great restaurant'
        }
        
        form = RestaurantForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        
    def test_restaurant_form_invalid_email(self):
        """Test restaurant form with invalid email"""
        form_data = {
            'name': 'Test Restaurant',
            'email': 'invalid-email'
        }
        
        form = RestaurantForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)


class MenuItemFormTest(TestCase):
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
            slug='pizza',
            is_active=True
        )
        
    def test_valid_menu_item_form(self):
        """Test creating menu item with valid data"""
        form_data = {
            'name': 'Margherita Pizza',
            'description': 'Classic margherita pizza with fresh basil',
            'category': self.category.pk,
            'price': '15.99',
            'discounted_price': '',
            'preparation_time': 20,
            'serving_size': '1 pizza',
            'calories': 300,
            'is_vegetarian': True,
            'is_vegan': False,
            'is_gluten_free': False,
            'is_available': True,
            'is_featured': False
        }
        
        form = MenuItemForm(data=form_data)
        self.assertTrue(form.is_valid())
        
    def test_menu_item_form_missing_required_fields(self):
        """Test menu item form with missing required fields"""
        form_data = {
            'description': 'A great pizza'
        }
        
        form = MenuItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('price', form.errors)
        
    def test_menu_item_form_invalid_price(self):
        """Test menu item form with invalid price"""
        form_data = {
            'name': 'Test Pizza',
            'price': 'invalid-price',
            'category': self.category.pk
        }
        
        form = MenuItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('price', form.errors)
        
    def test_menu_item_form_negative_price(self):
        """Test menu item form with negative price"""
        form_data = {
            'name': 'Test Pizza',
            'price': '-5.00',
            'category': self.category.pk
        }
        
        form = MenuItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        
    def test_menu_item_form_discount_higher_than_price(self):
        """Test menu item form with discount higher than regular price"""
        form_data = {
            'name': 'Test Pizza',
            'price': '10.00',
            'discounted_price': '15.00',
            'category': self.category.pk
        }
        
        form = MenuItemForm(data=form_data)
        # This should still be valid at form level, business logic handles it
        self.assertTrue(form.is_valid())
