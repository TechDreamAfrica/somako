"""
Management command to import products from a CSV or JSON file
Usage:
    python manage.py import_products --file products.csv
    python manage.py import_products --file products.json --format json
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from shop.models import Product, ProductVariant, Category
from decimal import Decimal
import csv
import json
import logging
from django.utils.text import slugify

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'Import products from CSV or JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Path to the import file'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['csv', 'json'],
            default='csv',
            help='File format (csv or json)'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Username of user to credit as creator'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        file_format = options['format']
        username = options.get('user')

        # Get user
        user = None
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f'User "{username}" does not exist')
        else:
            user = User.objects.filter(is_superuser=True).first()

        try:
            if file_format == 'csv':
                products = self.import_from_csv(file_path, user)
            else:
                products = self.import_from_json(file_path, user)

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully imported {len(products)} products!'
                )
            )

        except FileNotFoundError:
            raise CommandError(f'File not found: {file_path}')
        except Exception as e:
            raise CommandError(f'Error importing products: {str(e)}')

    def import_from_csv(self, file_path, user):
        """Import products from CSV file"""
        products = []

        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                product = self.create_product_from_dict(row, user)
                if product:
                    products.append(product)
                    self.stdout.write(f'Imported: {product.name}')

        return products

    def import_from_json(self, file_path, user):
        """Import products from JSON file"""
        products = []

        with open(file_path, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)

            for item in data:
                product = self.create_product_from_dict(item, user)
                if product:
                    products.append(product)
                    self.stdout.write(f'Imported: {product.name}')

        return products

    def create_product_from_dict(self, data, user):
        """Create product from dictionary data"""
        try:
            # Get or create category
            category_name = data.get('category', 'Uncategorized')
            category, _ = Category.objects.get_or_create(
                slug=slugify(category_name),
                defaults={'name': category_name}
            )

            # Generate unique SKU
            sku = data.get('sku', slugify(data['name'])[:50])
            counter = 1
            original_sku = sku
            while Product.objects.filter(sku=sku).exists():
                sku = f"{original_sku}-{counter}"
                counter += 1

            # Create product
            product = Product.objects.create(
                name=data['name'][:300],
                description=data.get('description', ''),
                short_description=data.get('short_description', '')[:500],
                category=category,
                base_price=Decimal(str(data.get('price', 0))),
                discount_percentage=Decimal(str(data.get('discount', 0))),
                sku=sku,
                brand=data.get('brand', ''),
                is_active=data.get('is_active', True),
                is_featured=data.get('is_featured', False),
                created_by=user
            )

            # Create default variant
            variant_sku = f"{sku}-default"
            ProductVariant.objects.create(
                product=product,
                sku=variant_sku,
                name='Default',
                stock_quantity=int(data.get('stock', 0)),
                is_active=True
            )

            return product

        except Exception as e:
            logger.error(f"Error creating product: {str(e)}")
            return None
