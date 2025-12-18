"""
Management command to scrape products from AliExpress
Usage:
    python manage.py scrape_aliexpress --keyword "phone accessories" --count 10
    python manage.py scrape_aliexpress --mock --count 15
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from shop.scrapers import AliExpressScraper, MockAliExpressScraper
from shop.models import Category
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'Scrape products from AliExpress and import them into the shop'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keyword',
            type=str,
            help='Search keyword for products'
        )
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of products to import (default: 10)'
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Category slug to assign products to'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Username of user to credit as creator (default: first superuser)'
        )
        parser.add_argument(
            '--mock',
            action='store_true',
            help='Use mock scraper for testing (generates fake products)'
        )

    def handle(self, *args, **options):
        keyword = options.get('keyword')
        count = options.get('count')
        category_slug = options.get('category')
        username = options.get('user')
        use_mock = options.get('mock')

        # Get or create user
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f'User "{username}" does not exist')
        else:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                self.stdout.write(
                    self.style.WARNING('No superuser found. Products will be created without a creator.')
                )

        # Get category if specified
        category = None
        if category_slug:
            try:
                category = Category.objects.get(slug=category_slug)
                self.stdout.write(
                    self.style.SUCCESS(f'Using category: {category.name}')
                )
            except Category.DoesNotExist:
                raise CommandError(f'Category with slug "{category_slug}" does not exist')

        # Use mock scraper or real scraper
        if use_mock:
            self.stdout.write(
                self.style.WARNING('Using MOCK scraper - generating fake products')
            )
            scraper = MockAliExpressScraper()
            products = scraper.bulk_generate(
                count=count,
                category=category,
                created_by=user
            )
        else:
            if not keyword:
                raise CommandError('--keyword is required when not using --mock mode')

            self.stdout.write(
                self.style.WARNING(
                    f'Scraping AliExpress for "{keyword}"...'
                )
            )
            scraper = AliExpressScraper()
            products = scraper.bulk_import(
                keyword=keyword,
                max_products=count,
                category=category,
                created_by=user
            )

        # Display results
        if products:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully imported {len(products)} products!'
                )
            )
            self.stdout.write('\nImported products:')
            for product in products:
                self.stdout.write(
                    f'  • {product.name} (SKU: {product.sku}) - ${product.base_price}'
                )
        else:
            self.stdout.write(
                self.style.ERROR('No products were imported')
            )
