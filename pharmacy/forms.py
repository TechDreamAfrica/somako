"""Forms for Pharmacy app"""
from django import forms
from django.utils.text import slugify
from .models import Medicine, Pharmacy


class PharmacyForm(forms.ModelForm):
    """Form for creating/updating pharmacies"""

    class Meta:
        model = Pharmacy
        fields = [
            'name', 'description', 'address', 'city', 'state', 'postal_code', 'country',
            'phone', 'email', 'website', 'latitude', 'longitude',
            'license_number', 'license_type', 'license_expiry_date', 'registration_number',
            'opening_hours', 'is_24_hours', 'delivery_available',
            'minimum_order_amount', 'delivery_fee', 'free_delivery_threshold', 'estimated_delivery_time',
            'logo', 'image', 'status', 'is_featured'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pharmacy name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe your pharmacy'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Full address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State/Region'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal code'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+233 XXX XXX XXX'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'pharmacy@example.com'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'License number'}),
            'license_type': forms.Select(attrs={'class': 'form-control'}),
            'license_expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Registration number'}),
            'opening_hours': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Mon-Fri: 8AM-9PM, Sat: 9AM-6PM'}),
            'is_24_hours': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'delivery_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'minimum_order_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'delivery_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'free_delivery_threshold': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'estimated_delivery_time': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Minutes'}),
            'logo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].required = False
        self.fields['status'].initial = 'active'

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            base_slug = slugify(instance.name)
            slug = base_slug
            counter = 1
            while Pharmacy.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            instance.slug = slug
        if commit:
            instance.save()
        return instance


class MedicineForm(forms.ModelForm):
    """Form for creating/updating medicines"""
    class Meta:
        model = Medicine
        fields = [
            'pharmacy', 'name', 'generic_name', 'brand_name', 'category', 'description', 'usage',
            'dosage', 'dosage_form', 'active_ingredients', 'side_effects', 'warnings',
            'storage_instructions', 'requires_prescription', 'prescription_type',
            'price', 'discount_price', 'stock_quantity', 'low_stock_threshold',
            'manufacturer', 'country_of_origin', 'pack_size', 'expiry_date', 'batch_number',
            'image', 'image_2', 'image_3', 'is_active', 'is_featured'
        ]
        widgets = {
            'pharmacy': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'generic_name': forms.TextInput(attrs={'class': 'form-control'}),
            'brand_name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'usage': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'dosage': forms.TextInput(attrs={'class': 'form-control'}),
            'dosage_form': forms.Select(attrs={'class': 'form-control'}),
            'active_ingredients': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'side_effects': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'warnings': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'storage_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'requires_prescription': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'prescription_type': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'low_stock_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control'}),
            'country_of_origin': forms.TextInput(attrs={'class': 'form-control'}),
            'pack_size': forms.TextInput(attrs={'class': 'form-control'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'batch_number': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'image_2': forms.FileInput(attrs={'class': 'form-control'}),
            'image_3': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['pharmacy'].queryset = Pharmacy.objects.filter(owner=user)
