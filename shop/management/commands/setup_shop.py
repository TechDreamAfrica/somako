"""
Management command to quickly setup shop with sample products
Usage:
    python manage.py setup_shop
    python manage.py setup_shop --products 30
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from shop.scrapers import MockAliExpressScraper
from shop.models import Category, Product, ProductVariant
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'Quick setup: Create categories and generate sample products for the shop'

    def add_arguments(self, parser):
        parser.add_argument(
            '--products',
            type=int,
            default=25,
            help='Total number of products to generate (default: 25)'
        )
        parser.add_argument(
            '--activate',
            action='store_true',
            help='Automatically activate all products and variants'
        )

    def handle(self, *args, **options):
        total_products_count = options['products']
        auto_activate = options['activate']

        self.stdout.write(self.style.HTTP_INFO('=' * 70))
        self.stdout.write(self.style.HTTP_INFO('SOMA KO - Quick Shop Setup'))
        self.stdout.write(self.style.HTTP_INFO('=' * 70))

        # Get or create user
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.filter(is_staff=True).first()

        if user:
            self.stdout.write(f'\n✓ Using user: {user.username}')
        else:
            self.stdout.write(
                self.style.WARNING('\n⚠ No admin user found. Products will be created without owner.')
            )

        # Create categories
        self.stdout.write('\n📁 Creating categories...')
        categories_data = [
            ('Electronics', 'electronics', 'Electronic devices and gadgets'),
            ('Fashion & Apparel', 'fashion', 'Clothing, shoes, and accessories'),
            ('Home & Garden', 'home-garden', 'Home decor and garden supplies'),
            ('Sports & Outdoors', 'sports', 'Sports equipment and outdoor gear'),
            ('Health & Beauty', 'health-beauty', 'Health and beauty products'),
        ]

        categories = []
        for name, slug, description in categories_data:
            category, created = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'description': description,
                    'is_active': True
                }
            )
            categories.append(category)
            status = "Created" if created else "Already exists"
            self.stdout.write(f'   ✓ {name}: {status}')

        # Calculate products per category
        products_per_category = total_products_count // len(categories)
        remainder = total_products_count % len(categories)

        # Generate products
        self.stdout.write(f'\n🛍️  Generating {total_products_count} products...')
        scraper = MockAliExpressScraper()
        total_products = []

        for idx, category in enumerate(categories):
            # Distribute remainder among first categories
            count = products_per_category + (1 if idx < remainder else 0)

            self.stdout.write(f'\n   Category: {category.name}')
            products = scraper.bulk_generate(
                count=count,
                category=category,
                created_by=user
            )
            total_products.extend(products)
            self.stdout.write(
                self.style.SUCCESS(f'   ✓ Generated {len(products)} products')
            )

        # Activate products if requested
        if auto_activate:
            self.stdout.write('\n⚡ Activating all products and variants...')
            Product.objects.all().update(is_active=True)
            ProductVariant.objects.all().update(is_active=True)
            active_count = Product.objects.filter(is_active=True).count()
            variant_count = ProductVariant.objects.filter(is_active=True).count()
            self.stdout.write(
                self.style.SUCCESS(
                    f'   ✓ Activated {active_count} products and {variant_count} variants'
                )
            )

        # Summary
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('✅ SUCCESS!'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Total Products Created: {len(total_products)}')
        self.stdout.write(f'Categories: {len(categories)}')

        if auto_activate:
            self.stdout.write(
                self.style.SUCCESS('\n✓ Products are active and ready to view!')
            )
            self.stdout.write('Visit: /shop/products/')
        else:
            self.stdout.write(
                self.style.WARNING('\n⚠ Products are inactive. Activate them:')
            )
            self.stdout.write('1. Go to /admin/shop/product/')
            self.stdout.write('2. Select products and set is_active=True')
            self.stdout.write('Or run: python manage.py setup_shop --activate')

        self.stdout.write('\n' + '=' * 70)

        # Display sample products
        self.stdout.write('\nSample products:')
        for product in total_products[:5]:
            price_display = f'${product.base_price}'
            if product.discount_percentage > 0:
                price_display = f'${product.discounted_price} (was ${product.base_price})'
            self.stdout.write(
                f'  • {product.name} - {price_display}'
            )

        if len(total_products) > 5:
            self.stdout.write(f'  ... and {len(total_products) - 5} more')

        self.stdout.write('')
