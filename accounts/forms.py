from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import RoleApplication

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=False)
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
