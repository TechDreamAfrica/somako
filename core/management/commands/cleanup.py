from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from shop.models import Cart


class Command(BaseCommand):
    help = 'Clean up old data (carts, expired sessions, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to keep data (default: 30)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        old_date = timezone.now() - timedelta(days=days)

        self.stdout.write(self.style.WARNING(f'Cleaning data older than {days} days...'))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('DRY RUN - No data will be deleted'))

        # Clean old anonymous carts
        old_carts = Cart.objects.filter(
            updated_at__lt=old_date,
            user__isnull=True
        )
        cart_count = old_carts.count()
        
        if not dry_run:
            old_carts.delete()
            self.stdout.write(self.style.SUCCESS(f'✅ Deleted {cart_count} old anonymous carts'))
        else:
            self.stdout.write(self.style.NOTICE(f'Would delete {cart_count} old anonymous carts'))

        # Clean expired Django sessions
        if not dry_run:
            from django.core.management import call_command
            call_command('clearsessions')
            self.stdout.write(self.style.SUCCESS('✅ Cleaned expired sessions'))
        else:
            self.stdout.write(self.style.NOTICE('Would clean expired sessions'))

        # Summary
        if not dry_run:
            self.stdout.write(self.style.SUCCESS('\n🎉 Cleanup completed successfully!'))
        else:
            self.stdout.write(self.style.NOTICE('\n💡 This was a dry run. Add --no-dry-run to actually delete data.'))
