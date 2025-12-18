"""Forms for Ride app"""
from django import forms
from .models import Vehicle


class VehicleForm(forms.ModelForm):
    """Form for creating/updating vehicles"""
    class Meta:
        model = Vehicle
        fields = [
            'category', 'make', 'model', 'year', 'color', 'license_plate',
            'vin_number', 'registration_document', 'insurance_document',
            'insurance_expiry_date', 'road_worthiness_certificate',
            'roadworthiness_expiry_date', 'front_photo', 'back_photo',
            'side_photo', 'interior_photo', 'condition', 'is_active', 'is_primary'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'make': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Toyota, Honda'}),
            'model': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Camry, Civic'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': '1990', 'max': '2030'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'license_plate': forms.TextInput(attrs={'class': 'form-control'}),
            'vin_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vehicle Identification Number'}),
            'registration_document': forms.FileInput(attrs={'class': 'form-control'}),
            'insurance_document': forms.FileInput(attrs={'class': 'form-control'}),
            'insurance_expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'road_worthiness_certificate': forms.FileInput(attrs={'class': 'form-control'}),
            'roadworthiness_expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'front_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'back_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'side_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'interior_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'condition': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
