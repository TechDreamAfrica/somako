"""
Management command to scrape products from AliExpress
Usage:
    python manage.py scrape_aliexpress --keyword "phone accessories" --count 10
    python manage.py scrape_aliexpress --category "electronics" --count 20 --max-pages 5
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
    help = '''
Scrape products from AliExpress and import them into the shop.

Examples:
  # Mock mode - Generate fake products for testing
  python manage.py scrape_aliexpress --mock --count 10

  # Search by keyword
  python manage.py scrape_aliexpress --keyword "phone accessories" --count 5 --max-pages 2

  # Search by category (enhanced with pagination)
  python manage.py scrape_aliexpress --category "electronics" --count 10 --max-pages 3

Available categories: electronics, phones, computers, fashion, mens-fashion, 
home-garden, toys, sports, automotive, jewelry, health-beauty, bags-shoes

Note: Real scraping may be limited due to anti-bot protections. Use --mock for testing.
    '''

    def add_arguments(self, parser):
        parser.add_argument(
            '--keyword',
            type=str,
            help='Search keyword for products'
        )
        parser.add_argument(
            '--category',
            type=str,
            help='AliExpress category to scrape (electronics, phones, computers, fashion, etc.)'
        )
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of products to import (default: 10)'
        )
        parser.add_argument(
            '--max-pages',
            type=int,
            default=3,
            help='Maximum pages to scrape (default: 3)'
        )
        parser.add_argument(
            '--db-category',
            type=str,
            help='Database category slug to assign products to'
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
        category = options.get('category')
        count = options.get('count')
        max_pages = options.get('max_pages')
        db_category_slug = options.get('db_category')
        username = options.get('user')
        use_mock = options.get('mock')

        # Validation
        if not keyword and not category and not use_mock:
            raise CommandError('You must specify either --keyword, --category, or --mock')

        # Get or create user
        user = None
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

        # Get database category if specified
        db_category = None
        if db_category_slug:
            try:
                db_category = Category.objects.get(slug=db_category_slug)
                self.stdout.write(
                    self.style.SUCCESS(f'Using database category: {db_category.name}')
                )
            except Category.DoesNotExist:
                raise CommandError(f'Category with slug "{db_category_slug}" does not exist')

        # Use mock scraper or real scraper
        if use_mock:
            self.stdout.write(
                self.style.WARNING('Using MOCK scraper - generating fake products')
            )
            scraper = MockAliExpressScraper()
            products = scraper.bulk_generate(
                count=count,
                category=db_category,
                created_by=user
            )
            self.stdout.write(
                self.style.SUCCESS(f'Generated {len(products)} mock products')
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'Scraping AliExpress with enhanced scraper...'
                )
            )
            scraper = AliExpressScraper()
            
            if category and category in scraper.categories:
                self.stdout.write(f'Scraping category: {category}')
                products = scraper.bulk_import(
                    category=category,
                    max_products=count,
                    max_pages=max_pages,
                    db_category=db_category,
                    created_by=user
                )
            elif keyword:
                self.stdout.write(f'Scraping keyword: {keyword}')
                products = scraper.bulk_import(
                    keyword=keyword,
                    max_products=count,
                    max_pages=max_pages,
                    db_category=db_category,
                    created_by=user
                )
            else:
                if category:
                    available_cats = ', '.join(scraper.categories.keys())
                    raise CommandError(f'Invalid category "{category}". Available: {available_cats}')
                else:
                    raise CommandError('Either --keyword or valid --category is required')
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'AliExpress scraping completed! Imported {len(products)} products'
                )
            )

        # Display results summary
        if products:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\\n✅ Successfully imported {len(products)} products from AliExpress!'
                )
            )
            
            # Show first few products as examples
            for i, product in enumerate(products[:3]):
                self.stdout.write(f'  • {product.name} (${product.base_price}) - ID: {product.id}')
            
            if len(products) > 3:
                self.stdout.write(f'  ... and {len(products) - 3} more products')
        else:
            self.stdout.write(
                self.style.WARNING('No products were imported. Check your search terms or try --mock mode.')
            )
