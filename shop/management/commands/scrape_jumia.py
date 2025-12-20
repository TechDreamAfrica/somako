"""
Management command to scrape products from Jumia Ghana
Usage:
    python manage.py scrape_jumia --keyword "smartphones" --count 20
    python manage.py scrape_jumia --category "electronics" --count 50
    python manage.py scrape_jumia --all-categories --count 100
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from shop.scrapers import JumiaScraper
from shop.models import Category
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'Scrape products from Jumia Ghana and import them into the shop'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keyword',
            type=str,
            help='Search keyword for products'
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Specific category to scrape (electronics, fashion, phones-tablets, etc.)'
        )
        parser.add_argument(
            '--all-categories',
            action='store_true',
            help='Scrape from all available categories'
        )
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Number of products to import per category (default: 20)'
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
            '--max-pages',
            type=int,
            default=10,
            help='Maximum pages to scrape per category (default: 10)'
        )
        parser.add_argument(
            '--mock',
            action='store_true',
            help='Use mock mode to generate sample Jumia products for testing'
        )

    def handle(self, *args, **options):
        keyword = options.get('keyword')
        category = options.get('category')
        all_categories = options.get('all_categories')
        count = options.get('count')
        db_category_slug = options.get('db_category')
        user_username = options.get('user')
        max_pages = options.get('max_pages')
        mock_mode = options.get('mock')

        # Validation
        if not keyword and not category and not all_categories:
            raise CommandError('You must specify either --keyword, --category, or --all-categories')

        # Mock mode for testing
        if mock_mode:
            self.stdout.write(self.style.WARNING('Running in MOCK mode - generating sample products'))
            return self.handle_mock_mode(keyword, category, all_categories, count, db_category_slug, user_username)

        # Get or create user
        try:
            if user_username:
                user = User.objects.get(username=user_username)
            else:
                user = User.objects.filter(is_superuser=True).first()
                if not user:
                    raise CommandError('No superuser found. Please create a superuser first.')
        except User.DoesNotExist:
            raise CommandError(f'User "{user_username}" not found')

        # Get category if specified
        db_category = None
        if db_category_slug:
            try:
                db_category = Category.objects.get(slug=db_category_slug)
            except Category.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'Category "{db_category_slug}" not found. Products will be uncategorized.')
                )

        # Initialize scraper
        scraper = JumiaScraper()
        
        total_imported = 0
        
        try:
            if keyword:
                # Search by keyword
                self.stdout.write(f'Searching for products with keyword: "{keyword}"')
                product_urls = scraper.search_products(keyword, max_results=count)
                
                self.stdout.write(f'Found {len(product_urls)} products to scrape')
                
                imported_count = self._scrape_and_import_products(
                    scraper, product_urls, db_category, user
                )
                total_imported += imported_count
                
            elif category:
                # Scrape specific category
                if category not in scraper.categories:
                    available_cats = ', '.join(scraper.categories.keys())
                    raise CommandError(f'Invalid category "{category}". Available: {available_cats}')
                
                self.stdout.write(f'Scraping category: {category}')
                category_url = scraper.get_category_urls(category)[0]
                product_urls = scraper.scrape_category_products(category_url, max_products=count)
                
                self.stdout.write(f'Found {len(product_urls)} products in {category}')
                
                # Try to create/get category in database
                if not db_category:
                    db_category, created = Category.objects.get_or_create(
                        slug=category.replace('-', '_'),
                        defaults={
                            'name': category.replace('-', ' ').title(),
                            'description': f'Products from Jumia {category.replace("-", " ")} category'
                        }
                    )
                    if created:
                        self.stdout.write(f'Created category: {db_category.name}')
                
                imported_count = self._scrape_and_import_products(
                    scraper, product_urls, db_category, user
                )
                total_imported += imported_count
                
            elif all_categories:
                # Scrape all categories
                self.stdout.write('Scraping all categories...')
                
                for cat_name in scraper.categories.keys():
                    self.stdout.write(f'\\n--- Scraping category: {cat_name} ---')
                    
                    category_url = scraper.get_category_urls(cat_name)[0]
                    product_urls = scraper.scrape_category_products(category_url, max_products=count)
                    
                    self.stdout.write(f'Found {len(product_urls)} products in {cat_name}')
                    
                    # Create/get category in database
                    cat_db_category, created = Category.objects.get_or_create(
                        slug=cat_name.replace('-', '_'),
                        defaults={
                            'name': cat_name.replace('-', ' ').title(),
                            'description': f'Products from Jumia {cat_name.replace("-", " ")} category'
                        }
                    )
                    if created:
                        self.stdout.write(f'Created category: {cat_db_category.name}')
                    
                    imported_count = self._scrape_and_import_products(
                        scraper, product_urls, cat_db_category, user
                    )
                    total_imported += imported_count
                    
                    self.stdout.write(f'Imported {imported_count} products from {cat_name}')
            
            self.stdout.write(
                self.style.SUCCESS(f'\\nCompleted! Total products imported: {total_imported}')
            )
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\\nOperation interrupted by user'))
            self.stdout.write(f'Products imported so far: {total_imported}')
        except Exception as e:
            raise CommandError(f'Error during scraping: {str(e)}')

    def _scrape_and_import_products(self, scraper, product_urls, category, user):
        """Scrape and import a list of product URLs"""
        imported_count = 0
        
        for idx, url in enumerate(product_urls, 1):
            try:
                self.stdout.write(f'Scraping product {idx}/{len(product_urls)}: {url}')
                
                # Scrape product data
                product_data = scraper.scrape_product_data(url)
                
                if product_data:
                    # Import product
                    product = scraper.import_product(product_data, category=category, created_by=user)
                    
                    if product:
                        imported_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ Imported: {product.name} (#{product.id})')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'  ⚠ Failed to import product data')
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'  ⚠ Failed to scrape product data')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error processing {url}: {str(e)}')
                )
                continue
        
        return imported_count

    def handle_mock_mode(self, keyword, category, all_categories, count, db_category_slug, user_username):
        """Handle mock mode for testing"""
        # Get or create user
        try:
            if user_username:
                user = User.objects.get(username=user_username)
            else:
                user = User.objects.filter(is_superuser=True).first()
                if not user:
                    raise CommandError('No superuser found. Please create a superuser first.')
        except User.DoesNotExist:
            raise CommandError(f'User "{user_username}" not found')

        # Get category if specified
        db_category = None
        if db_category_slug:
            try:
                db_category = Category.objects.get(slug=db_category_slug)
            except Category.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'Category "{db_category_slug}" not found. Products will be uncategorized.')
                )

        from shop.scrapers import MockJumiaScraper
        scraper = MockJumiaScraper()
        
        total_imported = 0
        
        try:
            if keyword:
                # Mock keyword search
                self.stdout.write(f'Mock: Generating products for keyword: "{keyword}"')
                products = scraper.generate_by_keyword(keyword, count, db_category, user)
                total_imported = len(products)
                
            elif category:
                # Mock category scraping
                self.stdout.write(f'Mock: Generating products for category: {category}')
                products = scraper.generate_by_category(category, count, db_category, user)
                total_imported = len(products)
                
            elif all_categories:
                # Mock all categories
                self.stdout.write('Mock: Generating products for all categories...')
                for cat_name in scraper.categories.keys():
                    self.stdout.write(f'Mock: Generating {count} products for {cat_name}')
                    
                    # Create/get category
                    cat_db_category, created = Category.objects.get_or_create(
                        slug=cat_name.replace('-', '_'),
                        defaults={
                            'name': cat_name.replace('-', ' ').title(),
                            'description': f'Products from Jumia {cat_name.replace("-", " ")} category'
                        }
                    )
                    if created:
                        self.stdout.write(f'Created category: {cat_db_category.name}')
                    
                    products = scraper.generate_by_category(cat_name, count, cat_db_category, user)
                    total_imported += len(products)
                    self.stdout.write(f'Generated {len(products)} mock products for {cat_name}')
            
            self.stdout.write(
                self.style.SUCCESS(f'\\nMock mode completed! Total products generated: {total_imported}')
            )
            
        except Exception as e:
            raise CommandError(f'Error in mock mode: {str(e)}')