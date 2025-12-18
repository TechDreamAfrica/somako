"""
Management command to create test delivery riders
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from express_pwa.models import DeliveryDriverProfile
from decimal import Decimal
from datetime import date

User = get_user_model()


class Command(BaseCommand):
    help = 'Create test delivery riders for development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of test riders to create',
        )

    def handle(self, *args, **options):
        count = options['count']
        
        test_riders = [
            {
                'username': 'rider1',
                'email': 'rider1@example.com',
                'first_name': 'John',
                'last_name': 'Mensah',
                'phone_number': '+233240123456',
                'license': 'GH-12345-AB',
                'rating': '4.8',
                'deliveries': 45,
                'availability': 'ONLINE'
            },
            {
                'username': 'rider2', 
                'email': 'rider2@example.com',
                'first_name': 'Akua',
                'last_name': 'Asante',
                'phone_number': '+233241123456',
                'license': 'GH-54321-CD',
                'rating': '4.9',
                'deliveries': 62,
                'availability': 'ONLINE'
            },
            {
                'username': 'rider3',
                'email': 'rider3@example.com', 
                'first_name': 'Kwame',
                'last_name': 'Osei',
                'phone_number': '+233242123456',
                'license': 'GH-67890-EF',
                'rating': '4.7',
                'deliveries': 38,
                'availability': 'OFFLINE'
            },
            {
                'username': 'rider4',
                'email': 'rider4@example.com',
                'first_name': 'Ama',
                'last_name': 'Boateng', 
                'phone_number': '+233243123456',
                'license': 'GH-09876-GH',
                'rating': '4.6',
                'deliveries': 29,
                'availability': 'ONLINE'
            },
            {
                'username': 'rider5',
                'email': 'rider5@example.com',
                'first_name': 'Kofi',
                'last_name': 'Appiah',
                'phone_number': '+233244123456', 
                'license': 'GH-56789-IJ',
                'rating': '4.9',
                'deliveries': 71,
                'availability': 'OFFLINE'
            },
        ]

        created_count = 0
        
        for i, rider_data in enumerate(test_riders[:count]):
            try:
                # Create user if not exists
                user, user_created = User.objects.get_or_create(
                    username=rider_data['username'],
                    defaults={
                        'email': rider_data['email'],
                        'first_name': rider_data['first_name'],
                        'last_name': rider_data['last_name'],
                        'phone_number': rider_data['phone_number'],
                        'is_verified': True,
                    }
                )
                
                if user_created:
                    user.set_password('testpass123')
                    user.save()
                    self.stdout.write(f"Created user: {user.username}")
                
                # Create or update delivery driver profile
                profile, profile_created = DeliveryDriverProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'driver_license_number': rider_data['license'],
                        'license_expiry_date': date(2026, 12, 31),
                        'status': 'APPROVED',
                        'availability': rider_data['availability'],
                        'total_deliveries': rider_data['deliveries'],
                        'average_rating': Decimal(rider_data['rating']),
                    }
                )
                
                if profile_created:
                    self.stdout.write(
                        self.style.SUCCESS(f"Created rider profile: {user.get_full_name()} - {rider_data['rating']}★ ({rider_data['deliveries']} deliveries)")
                    )
                    created_count += 1
                else:
                    self.stdout.write(f"Rider profile already exists: {user.get_full_name()}")
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error creating rider {rider_data['username']}: {str(e)}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {created_count} test rider profiles!")
        )