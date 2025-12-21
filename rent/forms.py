"""
Forms for Rent app
"""
from django import forms
from .models import Property, Room, PropertyImage, Equipment, RentalMessage, RentalBooking


class PropertyForm(forms.ModelForm):
    """Form for creating/updating properties"""

    class Meta:
        model = Property
        fields = [
            'category', 'title', 'description', 'property_type',
            'address', 'city', 'region', 'country',
            'bedrooms', 'bathrooms', 'area_sqm',
            'price_per_period', 'rental_period', 'currency', 'security_deposit',
            'minimum_rental_years', 'pets_allowed', 'utilities_included', 'furnished', 'lease_terms',
            'amenities', 'is_available', 'available_from', 'main_image'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter property title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe your property'}),
            'property_type': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Region'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'bedrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'bathrooms': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'area_sqm': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'price_per_period': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'rental_period': forms.Select(attrs={'class': 'form-control'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'security_deposit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'minimum_rental_years': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '10', 'value': '1'}),
            'pets_allowed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'utilities_included': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'furnished': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'lease_terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional lease terms and conditions'}),
            'amenities': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Comma-separated amenities (e.g., Parking, WiFi, AC)'}),
            'available_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'main_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }


class RoomForm(forms.ModelForm):
    """Form for creating/updating rooms"""

    class Meta:
        model = Room
        fields = [
            'name', 'room_type', 'description',
            'size_sqm', 'has_private_bathroom', 'max_occupants',
            'price_per_month', 'amenities',
            'is_available', 'available_from', 'image'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Room 101, Master Bedroom'}),
            'room_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe the room'}),
            'size_sqm': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'has_private_bathroom': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_occupants': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'price_per_month': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'amenities': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Comma-separated amenities (e.g., AC, WiFi, Balcony)'}),
            'available_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }


class PropertyImageForm(forms.ModelForm):
    """Form for adding property images"""

    class Meta:
        model = PropertyImage
        fields = ['image', 'caption']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Image caption (optional)'}),
        }


class EquipmentForm(forms.ModelForm):
    """Form for creating/updating equipment"""

    class Meta:
        model = Equipment
        fields = [
            'category', 'name', 'description', 'brand', 'model', 'condition',
            'city', 'region',
            'price_per_period', 'rental_period', 'currency', 'security_deposit',
            'specifications', 'is_available', 'quantity_available', 'main_image'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Equipment name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'condition': forms.Select(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'region': forms.TextInput(attrs={'class': 'form-control'}),
            'price_per_period': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'rental_period': forms.Select(attrs={'class': 'form-control'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'security_deposit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'specifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'quantity_available': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'main_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }


class RentalBookingForm(forms.ModelForm):
    """Form for creating equipment rental bookings"""

    class Meta:
        model = RentalBooking
        fields = [
            'start_date', 'end_date', 'quantity', 'notes', 'payment_method'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date',
                'required': True
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date',
                'required': True
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '10',
                'value': '1',
                'required': True
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Any special requests or additional information...'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-control'
            })
        }

    def __init__(self, *args, **kwargs):
        self.equipment = kwargs.pop('equipment', None)
        super().__init__(*args, **kwargs)
        
        if self.equipment and self.equipment.listing_type == 'for_sale':
            # For sales, remove date fields
            self.fields.pop('start_date', None)
            self.fields.pop('end_date', None)


class RentalMessageForm(forms.ModelForm):
    """Form for sending messages between renters and owners"""

    class Meta:
        model = RentalMessage
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Type your message here...',
                'required': True
            }),
        }
