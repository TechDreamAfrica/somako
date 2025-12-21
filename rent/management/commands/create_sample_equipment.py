from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rent.models import Equipment, EquipmentCategory
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample equipment data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of equipment items to create',
        )

    def handle(self, *args, **options):
        count = options['count']
        
        # Get or create a user to be the owner
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.first()
        
        if not admin_user:
            self.stdout.write(
                self.style.ERROR('No users found. Create a user first.')
            )
            return

        # Ensure categories exist
        categories_data = [
            {'name': 'Power Tools', 'icon': 'fas fa-drill', 'description': 'Electric and battery-powered tools'},
            {'name': 'Construction Equipment', 'icon': 'fas fa-hard-hat', 'description': 'Heavy machinery and construction tools'},
            {'name': 'Gardening Tools', 'icon': 'fas fa-seedling', 'description': 'Tools for gardening and landscaping'},
            {'name': 'Party Equipment', 'icon': 'fas fa-music', 'description': 'Sound systems and party supplies'},
            {'name': 'Vehicles', 'icon': 'fas fa-truck', 'description': 'Trucks, vans, and other vehicles'},
            {'name': 'Cleaning Equipment', 'icon': 'fas fa-broom', 'description': 'Professional cleaning tools'},
        ]

        for cat_data in categories_data:
            category, created = EquipmentCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'icon': cat_data['icon'],
                    'description': cat_data['description']
                }
            )
            if created:
                self.stdout.write(f'Created category: {category.name}')

        # Sample equipment data
        equipment_samples = [
            {
                'name': 'Angle Grinder - Professional',
                'category': 'Power Tools',
                'description': 'High-performance angle grinder for cutting and grinding metal, concrete, and stone.',
                'brand': 'Bosch',
                'model': 'GWS 7-115',
                'condition': 'excellent',
                'city': 'Accra',
                'region': 'Greater Accra',
                'price_per_period': 15.00,
                'rental_period': 'daily',
                'specifications': 'Power: 720W, Disc Size: 115mm, Speed: 11,000 RPM'
            },
            {
                'name': 'Scaffolding Set - Complete',
                'category': 'Construction Equipment',
                'description': 'Complete scaffolding system for construction and maintenance work. Includes all necessary components.',
                'brand': 'PERI',
                'model': 'PERI UP',
                'condition': 'good',
                'city': 'Kumasi',
                'region': 'Ashanti',
                'price_per_period': 120.00,
                'rental_period': 'weekly',
                'specifications': 'Height: up to 6m, Platform width: 1.09m, Load capacity: 200kg/m²'
            },
            {
                'name': 'Pressure Washer - Industrial',
                'category': 'Cleaning Equipment',
                'description': 'Heavy-duty pressure washer for cleaning driveways, buildings, and equipment.',
                'brand': 'Kärcher',
                'model': 'HD 5/11 C',
                'condition': 'excellent',
                'city': 'Takoradi',
                'region': 'Western',
                'price_per_period': 40.00,
                'rental_period': 'daily',
                'specifications': 'Pressure: 110 bar, Flow rate: 500 l/h, Motor: 2.3 kW'
            },
            {
                'name': 'Lawn Mower - Self-Propelled',
                'category': 'Gardening Tools',
                'description': 'Professional self-propelled lawn mower for large lawns and commercial landscaping.',
                'brand': 'Honda',
                'model': 'HRX537C5',
                'condition': 'good',
                'city': 'Accra',
                'region': 'Greater Accra',
                'price_per_period': 30.00,
                'rental_period': 'daily',
                'specifications': 'Engine: 160cc OHC, Cutting width: 53cm, Bag capacity: 88L'
            },
            {
                'name': 'Lighting Rig - Professional',
                'category': 'Party Equipment',
                'description': 'Complete professional lighting setup with LED spots, wash lights, and controller.',
                'brand': 'Chauvet',
                'model': 'DJ Complete Pack',
                'condition': 'new',
                'city': 'Tema',
                'region': 'Greater Accra',
                'price_per_period': 200.00,
                'rental_period': 'daily',
                'specifications': '8x LED Par lights, 2x Moving heads, DMX controller, Cables included'
            },
            {
                'name': 'Pickup Truck - Toyota Hilux',
                'category': 'Vehicles',
                'description': 'Reliable pickup truck for transportation and delivery services. Clean and well-maintained.',
                'brand': 'Toyota',
                'model': 'Hilux 2.4 GD-6',
                'condition': 'excellent',
                'city': 'Kumasi',
                'region': 'Ashanti',
                'price_per_period': 250.00,
                'rental_period': 'daily',
                'specifications': 'Engine: 2.4L Diesel, Transmission: Manual, Payload: 1000kg'
            },
            {
                'name': 'Welding Machine - Portable',
                'category': 'Power Tools',
                'description': 'Portable MIG/TIG welding machine suitable for both professional and DIY projects.',
                'brand': 'Lincoln Electric',
                'model': 'PowerMIG 210',
                'condition': 'excellent',
                'city': 'Takoradi',
                'region': 'Western',
                'price_per_period': 60.00,
                'rental_period': 'daily',
                'specifications': 'Output: 30-210A, Wire Speed: 50-700 IPM, Input: 208/230V'
            },
            {
                'name': 'Generator - Silent Type',
                'category': 'Construction Equipment',
                'description': 'Silent diesel generator for construction sites and events. Reliable power supply.',
                'brand': 'Perkins',
                'model': '1103A-33TG1',
                'condition': 'good',
                'city': 'Accra',
                'region': 'Greater Accra',
                'price_per_period': 150.00,
                'rental_period': 'daily',
                'specifications': 'Power: 33kVA, Fuel: Diesel, Noise level: <65dB(A), Runtime: 10hrs'
            },
        ]

        created_count = 0
        for i in range(min(count, len(equipment_samples))):
            item = equipment_samples[i]
            category = EquipmentCategory.objects.get(name=item['category'])
            
            equipment, created = Equipment.objects.get_or_create(
                name=item['name'],
                owner=admin_user,
                defaults={
                    'category': category,
                    'description': item['description'],
                    'brand': item['brand'],
                    'model': item['model'],
                    'condition': item['condition'],
                    'city': item['city'],
                    'region': item['region'],
                    'price_per_period': Decimal(str(item['price_per_period'])),
                    'rental_period': item['rental_period'],
                    'specifications': item['specifications'],
                    'is_available': True,
                    'quantity_available': 1,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'Created: {equipment.name}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} equipment items')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Total equipment items: {Equipment.objects.count()}')
        )