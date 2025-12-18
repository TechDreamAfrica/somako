"""
Management command to generate order numbers for orders that don't have them
"""
from django.core.management.base import BaseCommand
import uuid
from food.models import Order


class Command(BaseCommand):
    help = 'Generate order numbers for existing orders without order numbers'

    def handle(self, *args, **options):
        # Find orders without order numbers
        orders_without_numbers = Order.objects.filter(
            order_number__isnull=True
        ) | Order.objects.filter(order_number='')

        count = orders_without_numbers.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('All orders already have order numbers!'))
            return

        self.stdout.write(f'Found {count} orders without order numbers. Generating...')

        for order in orders_without_numbers:
            # Generate order number using the same format as in views
            order_number = f'FO-{order.created_at.strftime("%Y%m%d")}-{uuid.uuid4().hex[:8].upper()}'
            order.order_number = order_number
            order.save(update_fields=['order_number'])
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ Generated order number {order_number} for Order ID {order.id}')
            )

        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully generated order numbers for {count} orders!')
        )
