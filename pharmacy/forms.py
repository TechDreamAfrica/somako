"""Forms for Pharmacy app"""
from django import forms
from .models import Medicine


class MedicineForm(forms.ModelForm):
    """Form for creating/updating medicines"""
    class Meta:
        model = Medicine
        fields = [
            'name', 'generic_name', 'brand_name', 'category', 'description', 'usage',
            'dosage', 'dosage_form', 'active_ingredients', 'side_effects', 'warnings',
            'storage_instructions', 'requires_prescription', 'prescription_type',
            'price', 'discount_price', 'stock_quantity', 'low_stock_threshold',
            'manufacturer', 'country_of_origin', 'pack_size', 'expiry_date', 'batch_number',
            'image', 'image_2', 'image_3', 'is_active', 'is_featured'
        ]
        widgets = {
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
