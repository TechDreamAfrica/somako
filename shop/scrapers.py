"""
AliExpress Product Scraper
This module scrapes products from AliExpress and imports them into the shop.
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import random
from decimal import Decimal
from django.core.files.base import ContentFile
from django.utils.text import slugify
from .models import Product, ProductImage, ProductVariant, Category
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class AliExpressScraper:
    """Scraper for AliExpress products"""

    def __init__(self):
        self.base_url = "https://www.aliexpress.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def search_products(self, keyword, max_results=20):
        """
        Search for products on AliExpress

        Args:
            keyword: Search term
            max_results: Maximum number of products to return

        Returns:
            List of product URLs
        """
        search_url = f"{self.base_url}/wholesale?SearchText={keyword.replace(' ', '+')}"

        try:
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract product links (this selector may need adjustment)
            product_links = []
            for link in soup.find_all('a', class_='_1OUGS'):
                href = link.get('href')
                if href and '/item/' in href:
                    full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                    product_links.append(full_url)
                    if len(product_links) >= max_results:
                        break

            logger.info(f"Found {len(product_links)} products for keyword: {keyword}")
            return product_links

        except Exception as e:
            logger.error(f"Error searching products: {str(e)}")
            return []

    def scrape_product_data(self, product_url):
        """
        Scrape product details from a product page

        Args:
            product_url: URL of the product page

        Returns:
            Dictionary containing product data
        """
        try:
            # Add delay to avoid being blocked
            time.sleep(random.uniform(1, 3))

            response = self.session.get(product_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract product data (selectors may need adjustment based on AliExpress structure)
            product_data = {}

            # Try to extract data from JSON-LD structured data
            json_data = self._extract_json_ld_data(soup)

            if json_data:
                product_data = {
                    'name': json_data.get('name', ''),
                    'description': json_data.get('description', ''),
                    'price': self._parse_price(json_data.get('offers', {}).get('price', '0')),
                    'currency': json_data.get('offers', {}).get('priceCurrency', 'USD'),
                    'images': json_data.get('image', []),
                    'brand': json_data.get('brand', {}).get('name', ''),
                    'rating': json_data.get('aggregateRating', {}).get('ratingValue', None),
                    'review_count': json_data.get('aggregateRating', {}).get('reviewCount', 0),
                }
            else:
                # Fallback to HTML parsing
                product_data = self._parse_html_data(soup)

            product_data['source_url'] = product_url
            logger.info(f"Successfully scraped product: {product_data.get('name', 'Unknown')}")
            return product_data

        except Exception as e:
            logger.error(f"Error scraping product {product_url}: {str(e)}")
            return None

    def _extract_json_ld_data(self, soup):
        """Extract structured JSON-LD data from page"""
        try:
            script_tag = soup.find('script', type='application/ld+json')
            if script_tag:
                data = json.loads(script_tag.string)
                if isinstance(data, list):
                    # Find the Product schema
                    for item in data:
                        if item.get('@type') == 'Product':
                            return item
                elif data.get('@type') == 'Product':
                    return data
        except Exception as e:
            logger.warning(f"Could not extract JSON-LD data: {str(e)}")
        return None

    def _parse_html_data(self, soup):
        """Fallback method to parse HTML directly"""
        product_data = {}

        try:
            # Title
            title_elem = soup.find('h1', class_='product-title-text')
            product_data['name'] = title_elem.text.strip() if title_elem else 'Unknown Product'

            # Price
            price_elem = soup.find('span', class_='product-price-value')
            if price_elem:
                product_data['price'] = self._parse_price(price_elem.text)
            else:
                product_data['price'] = Decimal('0.00')

            # Description
            desc_elem = soup.find('div', class_='product-description')
            product_data['description'] = desc_elem.text.strip() if desc_elem else ''

            # Images
            images = []
            img_elements = soup.find_all('img', class_='magnifier-image')
            for img in img_elements:
                src = img.get('src') or img.get('data-src')
                if src:
                    images.append(src)
            product_data['images'] = images

            product_data['brand'] = ''
            product_data['currency'] = 'USD'

        except Exception as e:
            logger.error(f"Error parsing HTML data: {str(e)}")

        return product_data

    def _parse_price(self, price_str):
        """Parse price string to Decimal"""
        try:
            # Remove currency symbols and convert to decimal
            clean_price = ''.join(c for c in str(price_str) if c.isdigit() or c == '.')
            return Decimal(clean_price) if clean_price else Decimal('0.00')
        except:
            return Decimal('0.00')

    def download_image(self, image_url):
        """Download image from URL"""
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            return ContentFile(response.content)
        except Exception as e:
            logger.error(f"Error downloading image {image_url}: {str(e)}")
            return None

    def import_product(self, product_data, category=None, created_by=None):
        """
        Import scraped product data into database

        Args:
            product_data: Dictionary containing product information
            category: Category object to assign product to
            created_by: User who initiated the import

        Returns:
            Created Product object or None
        """
        try:
            # Generate unique SKU
            base_sku = slugify(product_data['name'][:50])
            sku = base_sku
            counter = 1
            while Product.objects.filter(sku=sku).exists():
                sku = f"{base_sku}-{counter}"
                counter += 1

            # Create product
            product = Product.objects.create(
                name=product_data['name'][:300],
                description=product_data.get('description', 'Imported from AliExpress'),
                short_description=product_data.get('description', '')[:500],
                category=category or self._get_default_category(),
                base_price=product_data.get('price', Decimal('0.00')),
                sku=sku,
                brand=product_data.get('brand', ''),
                is_active=False,  # Set to inactive for review
                created_by=created_by
            )

            # Create default variant
            variant_sku = f"{sku}-default"
            variant = ProductVariant.objects.create(
                product=product,
                sku=variant_sku,
                name='Default',
                stock_quantity=0,  # Set stock manually later
                is_active=False
            )

            # Download and save images
            images = product_data.get('images', [])
            for idx, image_url in enumerate(images[:5]):  # Limit to 5 images
                image_content = self.download_image(image_url)
                if image_content:
                    image_name = f"{sku}_image_{idx}.jpg"
                    product_image = ProductImage.objects.create(
                        product=product,
                        image=ContentFile(image_content.read(), name=image_name),
                        is_primary=(idx == 0),
                        order=idx
                    )

            logger.info(f"Successfully imported product: {product.name}")
            return product

        except Exception as e:
            logger.error(f"Error importing product: {str(e)}")
            return None

    def _get_default_category(self):
        """Get or create default category for imported products"""
        category, created = Category.objects.get_or_create(
            slug='imported-products',
            defaults={
                'name': 'Imported Products',
                'description': 'Products imported from external sources'
            }
        )
        return category

    def bulk_import(self, keyword, max_products=10, category=None, created_by=None):
        """
        Search and import multiple products

        Args:
            keyword: Search keyword
            max_products: Maximum number of products to import
            category: Category to assign products to
            created_by: User who initiated the import

        Returns:
            List of imported Product objects
        """
        product_urls = self.search_products(keyword, max_products)
        imported_products = []

        for url in product_urls:
            product_data = self.scrape_product_data(url)
            if product_data:
                product = self.import_product(product_data, category, created_by)
                if product:
                    imported_products.append(product)
                    logger.info(f"Imported {len(imported_products)}/{len(product_urls)} products")

        logger.info(f"Bulk import completed. Successfully imported {len(imported_products)} products.")
        return imported_products


# Simplified scraper for testing without actual web scraping
class MockAliExpressScraper:
    """Mock scraper for testing purposes"""

    def generate_mock_product(self, name, category=None, created_by=None):
        """Generate a mock product for testing"""
        from decimal import Decimal
        import random

        try:
            sku = slugify(name)[:50]
            counter = 1
            while Product.objects.filter(sku=sku).exists():
                sku = f"{slugify(name)[:45]}-{counter}"
                counter += 1

            product = Product.objects.create(
                name=name,
                description=f"This is a great {name}. High quality product imported for testing.",
                short_description=f"Quality {name} at affordable price",
                category=category or self._get_default_category(),
                base_price=Decimal(str(random.uniform(10, 500))),
                discount_percentage=Decimal(str(random.choice([0, 5, 10, 15, 20]))),
                sku=sku,
                brand="Generic Brand",
                is_active=True,
                is_featured=random.choice([True, False]),
                created_by=created_by
            )

            # Create variant
            ProductVariant.objects.create(
                product=product,
                sku=f"{sku}-default",
                name="Standard",
                stock_quantity=random.randint(10, 100),
                is_active=True
            )

            logger.info(f"Generated mock product: {product.name}")
            return product

        except Exception as e:
            logger.error(f"Error generating mock product: {str(e)}")
            return None

    def _get_default_category(self):
        """Get or create default category"""
        category, created = Category.objects.get_or_create(
            slug='imported-products',
            defaults={
                'name': 'Imported Products',
                'description': 'Products imported from external sources'
            }
        )
        return category

    def bulk_generate(self, count=10, category=None, created_by=None):
        """Generate multiple mock products"""
        product_names = [
            "Wireless Bluetooth Headphones",
            "Smart Watch Pro",
            "USB-C Fast Charger",
            "Phone Camera Lens Kit",
            "Portable Power Bank 20000mAh",
            "LED Desk Lamp",
            "Wireless Mouse",
            "Laptop Stand Aluminum",
            "Phone Ring Holder",
            "Car Phone Mount",
            "Bluetooth Speaker",
            "Screen Protector Glass",
            "Phone Case Protective",
            "Cable Organizer Set",
            "Mini Tripod Stand"
        ]

        imported_products = []
        for i in range(min(count, len(product_names))):
            product = self.generate_mock_product(
                product_names[i],
                category=category,
                created_by=created_by
            )
            if product:
                imported_products.append(product)

        logger.info(f"Generated {len(imported_products)} mock products")
        return imported_products
