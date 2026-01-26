"""Forms for Shop app"""
from django import forms
from .models import Product, ProductImage, Shop


class ShopForm(forms.ModelForm):
    """Form for creating/updating shops"""
    class Meta:
        model = Shop
        fields = ['name', 'description', 'logo', 'image', 'phone', 'email', 'website',
                  'address', 'city', 'state', 'postal_code', 'country', 'business_type',
                  'opening_hours', 'delivery_available', 'delivery_fee', 'minimum_order_amount',
                  'estimated_delivery_time']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Shop name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe your shop'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+233...'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'shop@example.com'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Full address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State/Region'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal code'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'business_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Electronics, Fashion, Grocery'}),
            'opening_hours': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Mon-Fri: 9AM-6PM, Sat: 10AM-4PM'}),
            'delivery_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'delivery_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'minimum_order_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'estimated_delivery_time': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Minutes'}),
        }


class ProductForm(forms.ModelForm):
    """Form for creating/updating products"""
    
    # Add stock quantity field (not part of Product model, handled separately)
    stock_quantity = forms.IntegerField(
        min_value=0,
        initial=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Stock quantity',
            'min': '0'
        }),
        help_text='Initial stock quantity for this product'
    )
    
    class Meta:
        model = Product
        fields = ['shop', 'category', 'name', 'description', 'short_description', 'sku', 'brand',
                  'base_price', 'discount_percentage', 'is_active', 'is_featured']
        widgets = {
            'shop': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Full description'}),
            'short_description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Short description'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SKU code'}),
            'brand': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brand name'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # Only show shops owned by the current user
            self.fields['shop'].queryset = Shop.objects.filter(owner=user)
        
        # Pre-populate stock_quantity from existing product's default variant
        if self.instance and self.instance.pk:
            default_variant = self.instance.variants.filter(name='Default').first()
            if not default_variant:
                default_variant = self.instance.variants.first()
            if default_variant:
                self.fields['stock_quantity'].initial = default_variant.stock_quantity


class ProductImageForm(forms.ModelForm):
    """Form for uploading product images"""
    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'alt_text': forms.TextInput(attrs={'class': 'form-control'}),
        }
