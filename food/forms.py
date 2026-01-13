"""
Forms for Food app
"""
from django import forms
from django.utils.text import slugify
from .models import Restaurant, MenuItem


class RestaurantForm(forms.ModelForm):
    """Form for creating/updating restaurants"""

    class Meta:
        model = Restaurant
        fields = [
            'name', 'description', 'address', 'city', 'state', 'postal_code',
            'phone', 'email', 'latitude', 'longitude',
            'minimum_order_amount', 'delivery_time',
            'logo', 'image', 'status', 'is_featured'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Restaurant name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe your restaurant'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Full address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State/Region'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal code'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+233 XXX XXX XXX'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'restaurant@example.com'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'minimum_order_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'delivery_time': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Minutes'}),
            'logo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Auto-generate slug from name if not set
        if not instance.slug:
            base_slug = slugify(instance.name)
            slug = base_slug
            counter = 1
            while Restaurant.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            instance.slug = slug
        if commit:
            instance.save()
        return instance


class MenuItemForm(forms.ModelForm):
    """Form for creating/updating menu items"""

    class Meta:
        model = MenuItem
        fields = [
            'name', 'description', 'category',
            'price', 'discounted_price',
            'preparation_time', 'serving_size', 'calories',
            'is_vegetarian', 'is_vegan', 'is_gluten_free',
            'image', 'is_available', 'is_featured'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Menu item name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe the dish'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discounted_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'preparation_time': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Minutes'}),
            'serving_size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1 plate, 2 pieces'}),
            'calories': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Calories (optional)'}),
            'is_vegetarian': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_vegan': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_gluten_free': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Auto-generate slug from name if not set
        if not instance.slug:
            base_slug = slugify(instance.name)
            slug = base_slug
            counter = 1
            # Check for uniqueness within the restaurant
            while MenuItem.objects.filter(restaurant=instance.restaurant, slug=slug).exclude(pk=instance.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            instance.slug = slug
        if commit:
            instance.save()
        return instance
