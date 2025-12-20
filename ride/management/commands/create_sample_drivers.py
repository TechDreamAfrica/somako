"""
Management command to create sample drivers for testing the ride booking system
Usage:
    python manage.py create_sample_drivers
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from ride.models import DriverProfile, Vehicle, VehicleCategory
from decimal import Decimal
from datetime import date, timedelta
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample drivers and vehicles for testing ride booking system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of sample drivers to create (default: 5)'
        )

    def handle(self, *args, **options):
        count = options.get('count')

        # Sample driver data
        sample_drivers = [
            {
                'username': 'driver_kwame',
                'first_name': 'Kwame',
                'last_name': 'Asante',
                'email': 'kwame.asante@gmail.com',
                'phone': '+233241234567',
                'license': 'DL-ACC-001-2023',
                'location': 'Accra',
                'lat': 5.6037,
                'lng': -0.1870
            },
            {
                'username': 'driver_ama',
                'first_name': 'Ama',
                'last_name': 'Osei',
                'email': 'ama.osei@gmail.com', 
                'phone': '+233242345678',
                'license': 'DL-ACC-002-2023',
                'location': 'East Legon',
                'lat': 5.6108,
                'lng': -0.1473
            },
            {
                'username': 'driver_kofi',
                'first_name': 'Kofi',
                'last_name': 'Mensah',
                'email': 'kofi.mensah@gmail.com',
                'phone': '+233243456789',
                'license': 'DL-ACC-003-2023',
                'location': 'Airport Residential',
                'lat': 5.6051,
                'lng': -0.1749
            },
            {
                'username': 'driver_akua',
                'first_name': 'Akua',
                'last_name': 'Boateng',
                'email': 'akua.boateng@gmail.com',
                'phone': '+233244567890',
                'license': 'DL-ACC-004-2023',
                'location': 'Tema',
                'lat': 5.6698,
                'lng': 0.0166
            },
            {
                'username': 'driver_yaw',
                'first_name': 'Yaw',
                'last_name': 'Owusu',
                'email': 'yaw.owusu@gmail.com',
                'phone': '+233245678901',
                'license': 'DL-ACC-005-2023',
                'location': 'Spintex',
                'lat': 5.5916,
                'lng': -0.0948
            }
        ]

        # Sample profile picture URLs
        profile_pictures = [
            'https://i.pravatar.cc/150?img=1',
            'https://i.pravatar.cc/150?img=2',
            'https://i.pravatar.cc/150?img=3',
            'https://i.pravatar.cc/150?img=4',
            'https://i.pravatar.cc/150?img=5',
        ]

        created_drivers = []

        # Ensure we have vehicle categories
        try:
            car_category = VehicleCategory.objects.get(name='Standard Car')
        except VehicleCategory.DoesNotExist:
            car_category = VehicleCategory.objects.create(
                name='Standard Car',
                vehicle_type='CAR',
                description='4-seater standard car for city rides',
                base_fare=Decimal('5.00'),
                price_per_km=Decimal('2.50'),
                price_per_minute=Decimal('0.50'),
                max_passengers=4,
                is_active=True
            )
            self.stdout.write(f"Created vehicle category: {car_category.name}")

        # Create sample drivers
        for i in range(min(count, len(sample_drivers))):
            driver_data = sample_drivers[i]
            
            try:
                # Create or get user
                user, user_created = User.objects.get_or_create(
                    username=driver_data['username'],
                    defaults={
                        'first_name': driver_data['first_name'],
                        'last_name': driver_data['last_name'],
                        'email': driver_data['email'],
                        'phone_number': driver_data['phone'],
                        'location': driver_data['location'],
                        'profile_picture': profile_pictures[i],
                        'service_roles': 'driver'
                    }
                )

                if user_created:
                    user.set_password('testpass123')
                    user.save()
                    self.stdout.write(f"Created user: {user.username}")
                else:
                    self.stdout.write(f"User {user.username} already exists")

                # Create driver profile
                driver_profile, driver_created = DriverProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'driver_license_number': driver_data['license'],
                        'license_expiry_date': date.today() + timedelta(days=365*2),  # 2 years from now
                        'status': 'APPROVED',
                        'availability': 'ONLINE',
                        'current_latitude': Decimal(str(driver_data['lat'])),
                        'current_longitude': Decimal(str(driver_data['lng'])),
                        'total_rides': random.randint(50, 500),
                        'average_rating': Decimal(str(random.uniform(4.0, 5.0))),
                        # Required document fields for testing (using placeholder)
                        'license_document': 'placeholder/license.pdf',
                        'national_id': 'placeholder/id.pdf',
                    }
                )

                if driver_created:
                    self.stdout.write(f"Created driver profile: {driver_profile}")
                else:
                    # Update existing driver to be online and approved
                    driver_profile.status = 'APPROVED'
                    driver_profile.availability = 'ONLINE'
                    driver_profile.current_latitude = Decimal(str(driver_data['lat']))
                    driver_profile.current_longitude = Decimal(str(driver_data['lng']))
                    driver_profile.save()
                    self.stdout.write(f"Updated driver profile: {driver_profile}")

                # Create vehicle for driver
                vehicle, vehicle_created = Vehicle.objects.get_or_create(
                    driver=driver_profile,
                    category=car_category,
                    defaults={
                        'make': random.choice(['Toyota', 'Honda', 'Hyundai', 'Nissan']),
                        'model': random.choice(['Corolla', 'Camry', 'Civic', 'Elantra', 'Sentra']),
                        'year': random.randint(2018, 2024),
                        'license_plate': f'GH-{random.randint(1000, 9999)}-{random.randint(10, 99)}',
                        'color': random.choice(['White', 'Black', 'Silver', 'Blue', 'Red']),
                        'condition': 'EXCELLENT',
                        'insurance_expiry_date': date.today() + timedelta(days=365),  # 1 year from now
                        # Required document fields for testing (using placeholder)
                        'registration_document': 'placeholder/registration.pdf',
                        'insurance_document': 'placeholder/insurance.pdf',
                        'is_active': True,
                        'is_primary': True
                    }
                )

                if vehicle_created:
                    self.stdout.write(f"Created vehicle: {vehicle.make} {vehicle.model}")
                else:
                    vehicle.is_active = True
                    vehicle.is_primary = True
                    vehicle.save()
                    self.stdout.write(f"Updated vehicle: {vehicle.make} {vehicle.model}")

                created_drivers.append(driver_profile)

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating driver {driver_data["username"]}: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created/updated {len(created_drivers)} drivers with vehicles!'
            )
        )
        
        # Display summary
        online_drivers = DriverProfile.objects.filter(
            status='APPROVED',
            availability='ONLINE'
        ).count()
        
        self.stdout.write(f"Total online drivers: {online_drivers}")
        self.stdout.write("Drivers are ready for ride booking!")