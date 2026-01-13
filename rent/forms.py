"""
Forms for Rent app - Equipment Rental
"""
from django import forms
from .models import Equipment, EquipmentImage, RentalMessage, RentalBooking


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


class EquipmentImageForm(forms.ModelForm):
    """Form for adding equipment images"""

    class Meta:
        model = EquipmentImage
        fields = ['image', 'caption']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Image caption (optional)'}),
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
