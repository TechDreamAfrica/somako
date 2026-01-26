from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import RoleApplication

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(
        max_length=15, 
        required=True,
        help_text='Required for SMS verification. Format: 0XX XXX XXXX or +233 XX XXX XXXX'
    )
    location = forms.CharField(max_length=100, required=False)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'phone_number', 'location', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.phone_number = self.cleaned_data['phone_number']
        user.location = self.cleaned_data['location']
        user.service_roles = 'general'  # Default role for all new users

        if commit:
            user.save()

        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'location', 'bio', 'profile_picture']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }


class RoleApplicationForm(forms.ModelForm):
    """Form for users to apply for service roles"""

    class Meta:
        model = RoleApplication
        fields = ['role', 'reason', 'experience', 'document']
        widgets = {
            'role': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Why do you want to join as this role? What motivates you?'
            }),
            'experience': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your relevant experience, skills, or qualifications...'
            }),
            'document': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            # Exclude roles user already has
            current_roles = user.get_roles_list()
            # Exclude roles with pending applications
            pending_roles = RoleApplication.objects.filter(
                user=user,
                status='pending'
            ).values_list('role', flat=True)

            excluded_roles = set(current_roles + list(pending_roles))

            available_choices = [
                (role, label) for role, label in User.SERVICE_ROLE_CHOICES
                if role not in excluded_roles and role != 'general'
            ]

            self.fields['role'].choices = available_choices

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')

        if not role:
            raise forms.ValidationError("Please select a role.")

        return cleaned_data


class ProviderApplicationForm(forms.ModelForm):
    """Comprehensive form for provider applications with business details"""

    class Meta:
        model = RoleApplication
        fields = [
            'business_name', 'business_address', 'city', 'business_phone', 
            'business_email', 'business_type', 'license_number', 
            'years_in_business', 'experience', 'reason', 'document', 'business_license'
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'placeholder': 'Enter your business name',
                'required': True
            }),
            'business_address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'rows': 2,
                'placeholder': 'Enter your business address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'placeholder': 'City',
                'required': True
            }),
            'business_phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'placeholder': '+233 XX XXX XXXX',
                'required': True
            }),
            'business_email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'placeholder': 'business@example.com'
            }),
            'business_type': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'placeholder': 'e.g., Fast Food, Electronics Store, Pharmacy'
            }),
            'license_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'placeholder': 'Business registration/license number'
            }),
            'years_in_business': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'placeholder': 'Years of experience',
                'min': 0
            }),
            'experience': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'rows': 3,
                'placeholder': 'Describe your experience and qualifications...'
            }),
            'reason': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'rows': 3,
                'placeholder': 'Why do you want to join Soma Ko as a provider?'
            }),
            'document': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx'
            }),
            'business_license': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.role = kwargs.pop('role', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Customize labels based on role
        role_labels = {
            'restaurant_owner': {
                'business_name': 'Restaurant Name',
                'business_type': 'Cuisine Type (e.g., Local, Chinese, Fast Food)',
            },
            'pharmacy_owner': {
                'business_name': 'Pharmacy Name',
                'business_type': 'Pharmacy Type (e.g., Community, Hospital)',
                'license_number': 'Pharmacy License Number',
            },
            'seller': {
                'business_name': 'Shop/Store Name',
                'business_type': 'Shop Category (e.g., Electronics, Fashion, Grocery)',
            },
            'landlord': {
                'business_name': 'Property Management Name (or your name)',
                'business_type': 'Property Types (e.g., Residential, Commercial)',
            },
            'equipment_owner': {
                'business_name': 'Equipment Rental Business Name',
                'business_type': 'Equipment Types (e.g., Construction, Events)',
            },
            'driver': {
                'business_name': 'Full Name',
                'business_type': 'Vehicle Type',
                'license_number': 'Driver License Number',
            },
            'delivery_driver': {
                'business_name': 'Full Name',
                'business_type': 'Vehicle Type (e.g., Motorcycle, Bicycle)',
                'license_number': 'Driver License Number',
            },
        }
        
        if self.role and self.role in role_labels:
            for field, label in role_labels[self.role].items():
                if field in self.fields:
                    self.fields[field].label = label

    def clean(self):
        cleaned_data = super().clean()
        
        # Validate required fields
        business_name = cleaned_data.get('business_name')
        city = cleaned_data.get('city')
        business_phone = cleaned_data.get('business_phone')
        
        if not business_name:
            self.add_error('business_name', 'Business name is required.')
        if not city:
            self.add_error('city', 'City is required.')
        if not business_phone:
            self.add_error('business_phone', 'Business phone is required.')
        
        return cleaned_data
