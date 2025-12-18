"""
Management command to automatically assign drivers to unassigned delivery requests
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from express_pwa.models import DeliveryRequest, DeliveryDriverProfile


class Command(BaseCommand):
    help = 'Automatically assign available drivers to unassigned delivery requests'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-age',
            type=int,
            default=60,
            help='Maximum age of unassigned deliveries to process (in minutes)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be assigned without actually assigning',
        )

    def handle(self, *args, **options):
        max_age_minutes = options['max_age']
        dry_run = options['dry_run']
        
        # Calculate cutoff time
        cutoff_time = timezone.now() - timedelta(minutes=max_age_minutes)
        
        # Find unassigned confirmed deliveries
        unassigned_deliveries = DeliveryRequest.objects.filter(
            status='confirmed',
            driver__isnull=True,
            created_at__gte=cutoff_time  # Only process recent ones
        ).order_by('created_at')
        
        self.stdout.write(
            f"Found {unassigned_deliveries.count()} unassigned deliveries created within the last {max_age_minutes} minutes"
        )
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No actual assignments will be made"))
        
        assigned_count = 0
        failed_count = 0
        
        for delivery in unassigned_deliveries:
            if dry_run:
                # Check if assignment would be possible
                available_drivers = DeliveryDriverProfile.objects.filter(
                    status='APPROVED',
                    availability='ONLINE'
                ).exclude(
                    user__assigned_deliveries__status__in=['assigned', 'picked_up', 'in_transit']
                )
                
                if available_drivers.exists():
                    self.stdout.write(
                        f"[DRY RUN] Would assign {delivery.tracking_number} "
                        f"({available_drivers.count()} drivers available)"
                    )
                    assigned_count += 1
                else:
                    self.stdout.write(
                        f"[DRY RUN] Cannot assign {delivery.tracking_number} - no available drivers"
                    )
                    failed_count += 1
            else:
                # Attempt actual assignment
                if delivery.auto_assign_driver():
                    assigned_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Assigned {delivery.tracking_number} to {delivery.driver.get_full_name()}"
                        )
                    )
                else:
                    failed_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"Failed to assign {delivery.tracking_number} - no available drivers"
                        )
                    )
        
        # Summary
        total_processed = assigned_count + failed_count
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"DRY RUN COMPLETE: {assigned_count} could be assigned, {failed_count} cannot be assigned"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"ASSIGNMENT COMPLETE: {assigned_count} assigned, {failed_count} failed, {total_processed} total processed"
                )
            )
            
        # Show current driver availability
        online_drivers = DeliveryDriverProfile.objects.filter(
            status='APPROVED',
            availability='ONLINE'
        ).count()
        
        busy_drivers = DeliveryDriverProfile.objects.filter(
            status='APPROVED',
            availability='ON_DELIVERY'
        ).count()
        
        self.stdout.write(
            f"Current driver status: {online_drivers} online and available, {busy_drivers} on delivery"
        )