"""
Django management command to create sample order data for testing
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from express_pwa.models import ExpressOrder, ExpressOrderItem, DeliveryRegion, DeliveryArea
from decimal import Decimal

class Command(BaseCommand):
    help = 'Create sample order data for testing'

    def handle(self, *args, **options):
        # Get or create a test user (driver)
        driver, created = User.objects.get_or_create(
            username='test_driver',
            defaults={
                'email': 'driver@test.com',
                'first_name': 'Test',
                'last_name': 'Driver'
            }
        )

        # Get or create a test user (sender) 
        sender, created = User.objects.get_or_create(
            username='test_sender',
            defaults={
                'email': 'sender@test.com',
                'first_name': 'Test', 
                'last_name': 'Sender'
            }
        )

        # Get first available regions/areas or create sample ones
        try:
            region = DeliveryRegion.objects.first()
            if not region:
                region = DeliveryRegion.objects.create(name="Greater Accra")
            
            area = DeliveryArea.objects.filter(region=region).first()
            if not area:
                area = DeliveryArea.objects.create(name="Accra Central", region=region)
        except:
            self.stdout.write("No regions found, creating sample regions...")
            return

        # Create sample orders with different statuses
        statuses = ['pending', 'in_progress', 'delivered']
        package_types = ['document', 'electronics', 'food']
        urgencies = ['standard', 'express', 'urgent']

        for i in range(3):
            # Create order
            order = ExpressOrder.objects.create(
                sender=sender,
                driver=driver if i > 0 else None,  # First order unassigned
                status='confirmed',
                special_instructions=f'Test order {i+1}'
            )

            # Create order item
            item = ExpressOrderItem.objects.create(
                order=order,
                driver=driver,
                recipient_name=f'Test Recipient {i+1}',
                recipient_phone=f'024412345{i}',
                package_type=package_types[i % len(package_types)],
                description=f'Test package {i+1}',
                weight=Decimal('1.5'),
                urgency=urgencies[i % len(urgencies)],
                pickup_region=region,
                pickup_area=area,
                pickup_address=f'Test Pickup Address {i+1}',
                delivery_region=region,
                delivery_area=area,
                delivery_address=f'Test Delivery Address {i+1}',
                estimated_cost=Decimal('25.00'),
                status=statuses[i % len(statuses)]
            )

            self.stdout.write(f'Created order {order.order_number} with item {item.item_number}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created 3 sample orders assigned to {driver.username}')
        )