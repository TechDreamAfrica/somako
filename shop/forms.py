"""Forms for Shop app"""
from django import forms
from .models import Product, ProductImage


class ProductForm(forms.ModelForm):
    """Form for creating/updating products"""
    class Meta:
        model = Product
        fields = ['category', 'name', 'description', 'short_description', 'sku', 'brand',
                  'base_price', 'discount_percentage', 'is_active', 'is_featured']
        widgets = {
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


class ProductImageForm(forms.ModelForm):
    """Form for uploading product images"""
    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'alt_text': forms.TextInput(attrs={'class': 'form-control'}),
        }
