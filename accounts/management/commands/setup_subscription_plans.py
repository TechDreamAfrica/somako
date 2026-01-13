"""
Management command to set up subscription plans with fees ranging from 20 to 100 cedis per month.
Usage: python manage.py setup_subscription_plans
"""
from django.core.management.base import BaseCommand
from accounts.subscription_models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Set up subscription plans with fees ranging from GHS 20 to GHS 100 per month'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete all existing plans before creating new ones',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('Deleting all existing subscription plans...'))
            SubscriptionPlan.objects.all().delete()

        # Define subscription plans
        plans = [
            {
                'name': 'basic',
                'display_name': 'Basic Plan',
                'description': 'Perfect for individuals just getting started. List your products/services and reach customers.',
                'price': 20.00,
                'max_listings': 5,
                'featured_listings': 0,
                'priority_support': False,
                'analytics_access': False,
                'verification_badge': False,
                'commission_rate': 5.00,
                'is_active': True,
                'is_popular': False,
                'sort_order': 1,
            },
            {
                'name': 'standard',
                'display_name': 'Standard Plan',
                'description': 'Great for growing businesses. Get more visibility with featured listings and analytics.',
                'price': 50.00,
                'max_listings': 20,
                'featured_listings': 3,
                'priority_support': True,
                'analytics_access': True,
                'verification_badge': False,
                'commission_rate': 3.50,
                'is_active': True,
                'is_popular': True,
                'sort_order': 2,
            },
            {
                'name': 'premium',
                'display_name': 'Premium Plan',
                'description': 'Best for established businesses. Unlimited listings, priority support, and verification badge.',
                'price': 100.00,
                'max_listings': -1,  # Unlimited
                'featured_listings': 10,
                'priority_support': True,
                'analytics_access': True,
                'verification_badge': True,
                'commission_rate': 2.00,
                'is_active': True,
                'is_popular': False,
                'sort_order': 3,
            },
        ]

        created_count = 0
        updated_count = 0

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.update_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created: {plan.display_name} - GHS {plan.price}/month')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Updated: {plan.display_name} - GHS {plan.price}/month')
                )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('Subscription Plans Summary:'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        
        for plan in SubscriptionPlan.objects.all().order_by('sort_order'):
            features = []
            if plan.max_listings == -1:
                features.append('Unlimited listings')
            else:
                features.append(f'{plan.max_listings} listings')
            if plan.featured_listings > 0:
                features.append(f'{plan.featured_listings} featured')
            if plan.priority_support:
                features.append('Priority support')
            if plan.analytics_access:
                features.append('Analytics')
            if plan.verification_badge:
                features.append('Verified badge')
            
            popular_tag = ' ⭐ POPULAR' if plan.is_popular else ''
            self.stdout.write(
                f'\n{plan.display_name}{popular_tag}'
            )
            self.stdout.write(f'  Price: GHS {plan.price}/month')
            self.stdout.write(f'  Commission: {plan.commission_rate}%')
            self.stdout.write(f'  Features: {", ".join(features)}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Done! Created: {created_count}, Updated: {updated_count}'))
