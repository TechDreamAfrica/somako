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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # AliExpress category mappings
        self.categories = {
            'electronics': 'consumer-electronics',
            'phones': 'phones-telecommunications',
            'computers': 'computer-office',
            'fashion': 'women-clothing',
            'mens-fashion': 'men-clothing',
            'home-garden': 'home-garden',
            'toys': 'toys-hobbies',
            'sports': 'sports-entertainment',
            'automotive': 'automobiles-motorcycles',
            'jewelry': 'jewelry-accessories',
            'health-beauty': 'beauty-health',
            'bags-shoes': 'luggage-bags'
        }

    def search_products(self, keyword, max_results=20, max_pages=5):
        """
        Search for products on AliExpress with pagination support

        Args:
            keyword: Search term
            max_results: Maximum number of products to return
            max_pages: Maximum pages to scrape

        Returns:
            List of product URLs
        """
        product_links = []
        page = 1
        
        try:
            while len(product_links) < max_results and page <= max_pages:
                search_url = f"{self.base_url}/wholesale?SearchText={keyword.replace(' ', '+')}&page={page}"
                logger.info(f"Scraping page {page}: {search_url}")
                
                # Add delay between pages
                if page > 1:
                    time.sleep(random.uniform(2, 4))
                
                response = self.session.get(search_url, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')

                # Multiple selectors for product links
                page_links = self._extract_product_links(soup)
                
                if not page_links:
                    logger.info(f"No products found on page {page}, stopping")
                    break
                
                # Remove duplicates and add to main list
                new_links = [link for link in page_links if link not in product_links]
                product_links.extend(new_links)
                
                logger.info(f"Found {len(new_links)} new products on page {page}")
                
                # Stop if no new products found
                if not new_links:
                    break
                    
                page += 1

            logger.info(f"Total found {len(product_links)} products for keyword: {keyword}")
            return product_links[:max_results]

        except Exception as e:
            logger.error(f"Error searching products: {str(e)}")
            return product_links[:max_results] if product_links else []

    def scrape_product_data(self, product_url):
        """
        Scrape product details from a product page with enhanced selectors

        Args:
            product_url: URL of the product page

        Returns:
            Dictionary containing product data
        """
        try:
            # Add delay to avoid being blocked
            time.sleep(random.uniform(2, 4))

            response = self.session.get(product_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract product data with multiple fallback methods
            product_data = {}

            # Try to extract data from JSON-LD structured data first
            json_data = self._extract_json_ld_data(soup)

            if json_data:
                product_data = self._parse_json_product_data(json_data)
            else:
                # Try extracting from script tags with product data
                script_data = self._extract_script_data(soup)
                if script_data:
                    product_data = self._parse_script_product_data(script_data)
                else:
                    # Fallback to HTML parsing with enhanced selectors
                    product_data = self._parse_html_data(soup)

            product_data['source_url'] = product_url
            
            # Validate essential fields
            if not product_data.get('name') or not product_data.get('price'):
                logger.warning(f"Missing essential data for product: {product_url}")
                return None
                
            logger.info(f"Successfully scraped product: {product_data.get('name', 'Unknown')[:50]}...")
            return product_data

        except Exception as e:
            logger.error(f"Error scraping product {product_url}: {str(e)}")
            return None
    def _extract_script_data(self, soup):
        """Extract product data from script tags"""
        try:
            # Look for script tags containing product data
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string and ('window.runParams' in script.string or 'productData' in script.string):
                    script_content = script.string
                    
                    # Try to extract JSON data from various patterns
                    patterns = [
                        r'window\.runParams\s*=\s*({.*?});',
                        r'productData\s*=\s*({.*?});',
                        r'"productInfo"\s*:\s*({.*?})',
                        r'"item"\s*:\s*({.*?})',
                    ]
                    
                    import re
                    for pattern in patterns:
                        match = re.search(pattern, script_content, re.DOTALL)
                        if match:
                            try:
                                return json.loads(match.group(1))
                            except:
                                continue
        except Exception as e:
            logger.debug(f"Could not extract script data: {str(e)}")
        return None
    
    def _parse_json_product_data(self, json_data):
        """Parse product data from JSON-LD structured data"""
        product_data = {
            'name': json_data.get('name', ''),
            'description': json_data.get('description', ''),
            'price': self._parse_price(json_data.get('offers', {}).get('price', '0')),
            'currency': json_data.get('offers', {}).get('priceCurrency', 'USD'),
            'images': json_data.get('image', []),
            'brand': json_data.get('brand', {}).get('name', '') if isinstance(json_data.get('brand'), dict) else str(json_data.get('brand', '')),
            'rating': json_data.get('aggregateRating', {}).get('ratingValue', None),
            'review_count': json_data.get('aggregateRating', {}).get('reviewCount', 0),
        }
        return product_data
    
    def _parse_script_product_data(self, script_data):
        """Parse product data from script variables"""
        product_data = {}
        
        try:
            # Navigate nested data structure
            item_data = script_data
            
            # Common paths in AliExpress data structure
            possible_paths = [
                ['data', 'item'],
                ['item'],
                ['productInfo'],
                ['data', 'productInfo'],
                ['skuInfo', 'productInfo']
            ]
            
            for path in possible_paths:
                temp_data = script_data
                for key in path:
                    if isinstance(temp_data, dict) and key in temp_data:
                        temp_data = temp_data[key]
                    else:
                        temp_data = None
                        break
                        
                if temp_data:
                    item_data = temp_data
                    break
            
            if isinstance(item_data, dict):
                product_data['name'] = item_data.get('title', item_data.get('name', ''))
                product_data['description'] = item_data.get('description', item_data.get('detail', ''))
                
                # Price extraction
                price_info = item_data.get('priceInfo', item_data.get('price', {}))
                if isinstance(price_info, dict):
                    price = price_info.get('minPrice', price_info.get('price', '0'))
                else:
                    price = price_info
                product_data['price'] = self._parse_price(price)
                
                # Images
                images = item_data.get('images', item_data.get('imageList', []))
                if isinstance(images, list):
                    product_data['images'] = [img.get('url', img) if isinstance(img, dict) else img for img in images]
                else:
                    product_data['images'] = []
                
                product_data['brand'] = item_data.get('brand', '')
                product_data['currency'] = 'USD'
                
        except Exception as e:
            logger.error(f"Error parsing script data: {str(e)}")
        
        return product_data

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
        """Enhanced HTML parsing with comprehensive selectors"""
        product_data = {}

        try:
            # Title with multiple selectors
            title_selectors = [
                'h1[data-pl="product-title"]',
                'h1.product-title-text',
                'h1.title',
                '.product-title h1',
                'h1[data-automation-id="product-title"]',
                '.pd-title',
                '.product-name h1',
                'h1'
            ]
            
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem and title_elem.get_text().strip():
                    product_data['name'] = title_elem.get_text().strip()
                    break
            
            if not product_data.get('name'):
                product_data['name'] = 'Unknown Product'

            # Price with multiple selectors
            price_selectors = [
                '.product-price-value',
                '[data-automation-id="product-price"]',
                '.price-current',
                '.notranslate',
                '.price .notranslate',
                '.uniform-banner-box-price',
                '.price-box .price',
                '.product-price .price'
            ]
            
            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem and price_elem.get_text().strip():
                    product_data['price'] = self._parse_price(price_elem.get_text())
                    break
            
            if not product_data.get('price'):
                product_data['price'] = Decimal('0.00')

            # Description with multiple selectors
            desc_selectors = [
                '.product-description',
                '[data-automation-id="product-description"]',
                '.description-content',
                '.product-overview',
                '.detail-desc',
                '.product-detail',
                '.product-info .description'
            ]
            
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem and desc_elem.get_text().strip():
                    product_data['description'] = desc_elem.get_text().strip()[:1000]  # Limit length
                    break
            
            if not product_data.get('description'):
                product_data['description'] = ''

            # Images with comprehensive selectors
            images = []
            img_selectors = [
                '.magnifier-image',
                '.product-image img',
                '.image-gallery img',
                '.product-photos img',
                '.slider-image img',
                '.thumb-img img',
                '.gallery-image img'
            ]
            
            for selector in img_selectors:
                img_elements = soup.select(selector)
                for img in img_elements:
                    src = img.get('src') or img.get('data-src') or img.get('data-original')
                    if src:
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = self.base_url + src
                        images.append(src)
                if images:
                    break
            
            product_data['images'] = list(set(images))[:10]  # Remove duplicates, limit to 10
            
            # Try to extract brand from title or other elements
            product_data['brand'] = self._extract_brand_from_title(product_data.get('name', ''))
            product_data['currency'] = 'USD'
            product_data['rating'] = None
            product_data['review_count'] = 0

        except Exception as e:
            logger.error(f"Error parsing HTML data: {str(e)}")

        return product_data
    
    def _extract_brand_from_title(self, title):
        """Extract brand from product title"""
        common_brands = [
            'Apple', 'Samsung', 'Huawei', 'Xiaomi', 'OnePlus', 'Google', 'LG', 'Sony',
            'Canon', 'Nikon', 'HP', 'Dell', 'Lenovo', 'Asus', 'Acer', 'Microsoft',
            'Nike', 'Adidas', 'Puma', 'Under Armour', 'Levi\'s', 'H&M', 'Zara'
        ]
        
        title_lower = title.lower()
        for brand in common_brands:
            if brand.lower() in title_lower:
                return brand
        
        # Try to extract first word as potential brand
        words = title.split()
        if words and len(words[0]) > 2:
            return words[0]
        
        return ''

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

    def bulk_import(self, keyword=None, category=None, max_products=10, max_pages=5, db_category=None, created_by=None):
        """
        Enhanced bulk import with category support

        Args:
            keyword: Search keyword (optional if category provided)
            category: Category to scrape (optional if keyword provided)
            max_products: Maximum number of products to import
            max_pages: Maximum pages to scrape per query
            db_category: Database category to assign products to
            created_by: User who initiated the import

        Returns:
            List of imported Product objects
        """
        imported_products = []
        
        try:
            # Get product URLs
            if keyword:
                product_urls = self.search_products(keyword, max_products, max_pages)
                logger.info(f"Found {len(product_urls)} products for keyword: {keyword}")
            elif category:
                product_urls = self.scrape_category_products(category, max_products, max_pages)
                logger.info(f"Found {len(product_urls)} products in category: {category}")
            else:
                logger.error("Either keyword or category must be provided")
                return imported_products
            
            if not product_urls:
                logger.warning("No product URLs found")
                return imported_products

            # Process each product URL
            for idx, url in enumerate(product_urls, 1):
                try:
                    logger.info(f"Processing product {idx}/{len(product_urls)}: {url[:80]}...")
                    
                    product_data = self.scrape_product_data(url)
                    if product_data:
                        product = self.import_product(product_data, db_category, created_by)
                        if product:
                            imported_products.append(product)
                            logger.info(f"✓ Imported: {product.name[:50]}... (ID: {product.id})")
                        else:
                            logger.warning(f"✗ Failed to import product data from {url}")
                    else:
                        logger.warning(f"✗ Failed to scrape product data from {url}")
                        
                    # Progress update
                    if idx % 5 == 0:
                        logger.info(f"Progress: {len(imported_products)}/{idx} products imported successfully")
                        
                except Exception as e:
                    logger.error(f"Error processing product {idx}: {str(e)}")
                    continue

            success_rate = len(imported_products) / len(product_urls) * 100 if product_urls else 0
            logger.info(f"Bulk import completed. Successfully imported {len(imported_products)}/{len(product_urls)} products ({success_rate:.1f}% success rate)")
            
        except Exception as e:
            logger.error(f"Error in bulk import: {str(e)}")
        
        return imported_products

    def _extract_product_links(self, soup):
        """Extract product links from search results page"""
        links = []
        
        # Multiple selectors to find product links
        selectors = [
            'a[href*="/item/"]',  # Standard item links
            '.product-item a',    # Product item containers
            '.item a',           # Item containers
            'a[href*="aliexpress.com/item"]',  # Full aliexpress item links
            '.card-item a',      # Card-style product items
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                href = element.get('href')
                if href:
                    # Convert relative URLs to absolute
                    if href.startswith('/'):
                        href = f"{self.base_url}{href}"
                    elif not href.startswith('http'):
                        continue
                    
                    # Filter valid product URLs
                    if '/item/' in href and href not in links:
                        links.append(href)
        
        logger.info(f"Extracted {len(links)} product links using selectors")
        return links

    def scrape_category_products(self, category, max_products=20, max_pages=5):
        """
        Scrape products from a specific AliExpress category

        Args:
            category: Category name from self.categories
            max_products: Maximum number of products to return
            max_pages: Maximum pages to scrape

        Returns:
            List of product URLs
        """
        if category not in self.categories:
            logger.error(f"Invalid category: {category}. Available: {list(self.categories.keys())}")
            return []

        category_slug = self.categories[category]
        product_links = []
        page = 1
        
        try:
            while len(product_links) < max_products and page <= max_pages:
                # Use category URL structure
                category_url = f"{self.base_url}/category/{category_slug}?page={page}"
                logger.info(f"Scraping category page {page}: {category_url}")
                
                # Add delay between pages
                if page > 1:
                    time.sleep(random.uniform(2, 4))
                
                response = self.session.get(category_url, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')

                # Extract product links
                page_links = self._extract_product_links(soup)
                
                if not page_links:
                    logger.info(f"No products found on category page {page}, stopping")
                    break
                
                # Remove duplicates and add to main list
                new_links = [link for link in page_links if link not in product_links]
                product_links.extend(new_links)
                
                logger.info(f"Found {len(new_links)} new products on category page {page}")
                
                # Stop if no new products found
                if not new_links:
                    logger.info(f"No new products on category page {page}, stopping pagination")
                    break
                
                page += 1
                
        except Exception as e:
            logger.error(f"Error scraping category {category}: {str(e)}")
        
        logger.info(f"Total found {len(product_links)} products in category: {category}")
        return product_links[:max_products]


# Simplified scraper for testing without actual web scraping

class JumiaScraper:
    """Scraper for Jumia Ghana products"""

    def __init__(self):
        self.base_url = "https://www.jumia.com.gh"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Referer': 'https://www.jumia.com.gh/'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Set additional session properties for better compatibility
        self.session.max_redirects = 5
        
        # Jumia category mappings (updated based on actual Jumia Ghana structure)
        self.categories = {
            'electronics': '/electronics/',
            'fashion': '/fashion/',
            'phones-tablets': '/phones-tablets/',
            'home-office': '/home-garden/',
            'beauty-health': '/beauty-health/',
            'kids-babies': '/baby-products/',
            'sports-fitness': '/sporting-goods/',
            'automobile': '/automobile/',
            'books-games': '/books-games-media/',
            'garden-outdoor': '/garden-outdoors/',
            'food-drinks': '/groceries/',
            'services': '/services/'
        }

    def get_category_urls(self, category_name=None):
        """
        Get URLs for product categories
        
        Args:
            category_name: Specific category to scrape, or None for all
        
        Returns:
            List of category URLs
        """
        if category_name and category_name in self.categories:
            return [f"{self.base_url}{self.categories[category_name]}"]
        
        return [f"{self.base_url}{url}" for url in self.categories.values()]

    def scrape_category_products(self, category_url, max_products=50):
        """
        Scrape products from a category page
        
        Args:
            category_url: URL of the category
            max_products: Maximum number of products to scrape
        
        Returns:
            List of product URLs
        """
        products = []
        page = 1
        
        try:
            while len(products) < max_products:
                # Jumia pagination format
                url = f"{category_url}?page={page}"
                logger.info(f"Scraping category page: {url}")
                
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find product links on the page
                product_links = soup.find_all('a', {'class': lambda x: x and 'core' in x.lower()})
                
                if not product_links:
                    # Try alternative selectors
                    product_links = soup.find_all('a', href=lambda href: href and '/products/' in href)
                
                page_products = []
                for link in product_links:
                    href = link.get('href')
                    if href and '/products/' in href:
                        if not href.startswith('http'):
                            href = self.base_url + href
                        page_products.append(href)
                
                if not page_products:
                    logger.info(f"No more products found on page {page}")
                    break
                
                # Remove duplicates and add to main list
                unique_products = [p for p in page_products if p not in products]
                products.extend(unique_products)
                
                logger.info(f"Found {len(unique_products)} products on page {page}")
                
                # Stop if we've reached the limit or no new products
                if len(unique_products) == 0 or len(products) >= max_products:
                    break
                
                page += 1
                # Add delay between pages
                time.sleep(random.uniform(2, 4))
                
        except Exception as e:
            logger.error(f"Error scraping category {category_url}: {str(e)}")
        
        return products[:max_products]

    def search_products(self, keyword, max_results=20):
        """
        Search for products on Jumia
        
        Args:
            keyword: Search term
            max_results: Maximum number of products to return
        
        Returns:
            List of product URLs
        """
        search_url = f"{self.base_url}/catalog/?q={keyword.replace(' ', '+')}"
        products = []
        page = 1
        
        try:
            while len(products) < max_results:
                url = f"{search_url}&page={page}"
                logger.info(f"Searching: {url}")
                
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find product links
                product_links = soup.find_all('a', href=lambda href: href and '/products/' in href)
                
                page_products = []
                for link in product_links:
                    href = link.get('href')
                    if href and '/products/' in href:
                        if not href.startswith('http'):
                            href = self.base_url + href
                        page_products.append(href)
                
                if not page_products:
                    break
                
                unique_products = [p for p in page_products if p not in products]
                products.extend(unique_products)
                
                if len(unique_products) == 0 or len(products) >= max_results:
                    break
                
                page += 1
                time.sleep(random.uniform(1, 3))
                
        except Exception as e:
            logger.error(f"Error searching products: {str(e)}")
            
        return products[:max_results]

    def scrape_product_data(self, product_url):
        """
        Scrape product details from a Jumia product page
        
        Args:
            product_url: URL of the product page
        
        Returns:
            Dictionary containing product data
        """
        try:
            time.sleep(random.uniform(1, 3))
            
            response = self.session.get(product_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            product_data = {}
            
            # Extract JSON-LD data first
            json_data = self._extract_jumia_json_data(soup)
            
            if json_data:
                product_data = self._parse_jumia_json_data(json_data)
            else:
                # Fallback to HTML parsing
                product_data = self._parse_jumia_html_data(soup)
            
            product_data['source_url'] = product_url
            logger.info(f"Successfully scraped Jumia product: {product_data.get('name', 'Unknown')}")
            return product_data
            
        except Exception as e:
            logger.error(f"Error scraping Jumia product {product_url}: {str(e)}")
            return None

    def _extract_jumia_json_data(self, soup):
        """Extract JSON data from Jumia product page"""
        try:
            # Look for JSON-LD structured data
            script_tags = soup.find_all('script', type='application/ld+json')
            for script in script_tags:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'Product':
                        return data
                    elif isinstance(data, list):
                        for item in data:
                            if item.get('@type') == 'Product':
                                return item
                except:
                    continue
            
            # Look for product data in script tags
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string and 'window.__INITIAL_STATE__' in script.string:
                    # Try to extract product data from the initial state
                    script_content = script.string
                    start = script_content.find('window.__INITIAL_STATE__')
                    if start > -1:
                        start = script_content.find('{', start)
                        if start > -1:
                            try:
                                # Extract the JSON part
                                bracket_count = 0
                                end = start
                                for i, char in enumerate(script_content[start:]):
                                    if char == '{':
                                        bracket_count += 1
                                    elif char == '}':
                                        bracket_count -= 1
                                        if bracket_count == 0:
                                            end = start + i + 1
                                            break
                                
                                json_str = script_content[start:end]
                                data = json.loads(json_str)
                                return data
                            except:
                                continue
        except Exception as e:
            logger.warning(f"Could not extract Jumia JSON data: {str(e)}")
        return None

    def _parse_jumia_json_data(self, json_data):
        """Parse JSON data from Jumia"""
        product_data = {}
        
        try:
            product_data['name'] = json_data.get('name', '')
            product_data['description'] = json_data.get('description', '')
            
            # Handle offers/pricing
            offers = json_data.get('offers', {})
            if isinstance(offers, list) and offers:
                offers = offers[0]
            
            price_str = offers.get('price', '0')
            product_data['price'] = self._parse_price(price_str)
            product_data['currency'] = offers.get('priceCurrency', 'GHS')
            
            # Images
            images = json_data.get('image', [])
            if isinstance(images, str):
                images = [images]
            product_data['images'] = images
            
            # Brand
            brand = json_data.get('brand', {})
            if isinstance(brand, dict):
                product_data['brand'] = brand.get('name', '')
            else:
                product_data['brand'] = str(brand) if brand else ''
            
            # Ratings
            rating_data = json_data.get('aggregateRating', {})
            product_data['rating'] = rating_data.get('ratingValue')
            product_data['review_count'] = rating_data.get('reviewCount', 0)
            
        except Exception as e:
            logger.error(f"Error parsing Jumia JSON data: {str(e)}")
        
        return product_data

    def _parse_jumia_html_data(self, soup):
        """Parse HTML data from Jumia product page"""
        product_data = {}
        
        try:
            # Product title
            title_selectors = [
                'h1.-fs20.-pts.-pbxs',
                'h1[data-automation-id="product-title"]',
                'h1.title',
                '.product-title h1',
                'h1'
            ]
            
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    product_data['name'] = title_elem.get_text().strip()
                    break
            
            if not product_data.get('name'):
                product_data['name'] = 'Unknown Product'
            
            # Price
            price_selectors = [
                '.prc',
                '.-b.-ltr.-tal.-fs24.-prxs',
                '[data-automation-id="product-price"]',
                '.price',
                '.current-price'
            ]
            
            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    product_data['price'] = self._parse_price(price_elem.get_text())
                    break
            
            if not product_data.get('price'):
                product_data['price'] = Decimal('0.00')
            
            # Description
            desc_selectors = [
                '.markup.-mhm.-pvl.-oxa.-bs',
                '.product-description',
                '[data-automation-id="product-description"]',
                '.description'
            ]
            
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    product_data['description'] = desc_elem.get_text().strip()
                    break
            
            if not product_data.get('description'):
                product_data['description'] = ''
            
            # Images
            images = []
            img_selectors = [
                '.sldr img',
                '.thumb img',
                '[data-automation-id="productImage"] img',
                '.product-images img'
            ]
            
            for selector in img_selectors:
                img_elements = soup.select(selector)
                for img in img_elements:
                    src = img.get('src') or img.get('data-src') or img.get('data-original')
                    if src:
                        if not src.startswith('http'):
                            src = 'https:' + src if src.startswith('//') else self.base_url + src
                        images.append(src)
                if images:
                    break
            
            product_data['images'] = list(set(images))  # Remove duplicates
            
            # Brand (try to extract from title or other elements)
            product_data['brand'] = self._extract_brand_from_title(product_data.get('name', ''))
            product_data['currency'] = 'GHS'
            product_data['rating'] = None
            product_data['review_count'] = 0
            
        except Exception as e:
            logger.error(f"Error parsing Jumia HTML data: {str(e)}")
        
        return product_data

    def _extract_brand_from_title(self, title):
        """Extract brand from product title"""
        common_brands = [
            'Samsung', 'Apple', 'iPhone', 'Huawei', 'Xiaomi', 'Tecno', 'Infinix',
            'Nokia', 'LG', 'Sony', 'Canon', 'Nikon', 'HP', 'Dell', 'Lenovo',
            'Asus', 'Acer', 'Microsoft', 'Nintendo', 'PlayStation', 'Xbox'
        ]
        
        title_lower = title.lower()
        for brand in common_brands:
            if brand.lower() in title_lower:
                return brand
        
        # Try to extract first word as potential brand
        words = title.split()
        if words:
            return words[0]
        
        return ''

    def _parse_price(self, price_str):
        """Parse price string to Decimal"""
        try:
            # Remove currency symbols and spaces
            import re
            clean_price = re.sub(r'[^\d.]', '', str(price_str))
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
        """Import scraped product data into database"""
        try:
            if not product_data or not product_data.get('name'):
                return None
            
            # Generate unique SKU
            base_sku = slugify(product_data['name'])[:20]
            sku = base_sku
            counter = 1
            while Product.objects.filter(sku=sku).exists():
                sku = f"{base_sku}-{counter}"
                counter += 1
            
            # Create product
            product = Product.objects.create(
                name=product_data['name'],
                description=product_data.get('description', ''),
                short_description=product_data.get('description', '')[:500] if product_data.get('description') else '',
                base_price=product_data.get('price', Decimal('0.00')),
                sku=sku,
                brand=product_data.get('brand', ''),
                category=category,
                created_by=created_by,
                is_active=True
            )
            
            # Download and save images
            for idx, image_url in enumerate(product_data.get('images', [])[:5]):  # Limit to 5 images
                image_file = self.download_image(image_url)
                if image_file:
                    image_name = f"{sku}_{idx + 1}.jpg"
                    ProductImage.objects.create(
                        product=product,
                        image=image_file,
                        alt_text=product_data['name'],
                        is_primary=(idx == 0)
                    )
            
            logger.info(f"Imported product: {product.name} (ID: {product.id})")
            return product
            
        except Exception as e:
            logger.error(f"Error importing product: {str(e)}")
            return None


class MockAliExpressScraper:
    """Mock scraper for testing purposes"""

    def generate_mock_product(self, name, category=None, created_by=None):
        """Generate a mock product for testing"""
        from decimal import Decimal
        import random

        try:
            # Generate unique slug
            base_slug = slugify(name)[:290]  # Leave room for counter
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            # Generate unique sku
            sku = slugify(name)[:50]
            counter = 1
            while Product.objects.filter(sku=sku).exists():
                sku = f"{slugify(name)[:45]}-{counter}"
                counter += 1

            product = Product.objects.create(
                name=name,
                slug=slug,
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
            # Electronics
            "Wireless Bluetooth Headphones",
            "Smart Watch Pro",
            "USB-C Fast Charger",
            "Phone Camera Lens Kit",
            "Portable Power Bank 20000mAh",
            "LED Desk Lamp",
            "Wireless Mouse",
            "Bluetooth Speaker",
            "Screen Protector Glass",
            "Phone Case Protective",
            "Cable Organizer Set",
            "Mini Tripod Stand",
            
            # Home & Kitchen
            "Air Fryer Digital",
            "Coffee Maker Automatic",
            "Electric Kettle Steel",
            "Food Storage Containers",
            "Non-Stick Frying Pan",
            "Microfiber Cleaning Cloth",
            "Kitchen Scale Digital",
            "Water Bottle Insulated",
            
            # Fashion & Accessories
            "Leather Wallet Men",
            "Sunglasses Polarized",
            "Watch Band Silicone",
            "Backpack Laptop 15.6",
            "Baseball Cap Cotton",
            "Scarf Cashmere Soft",
            "Belt Genuine Leather",
            "Jewelry Box Wooden",
            
            # Sports & Outdoors
            "Yoga Mat Anti-Slip",
            "Resistance Bands Set",
            "Water Bottle Sports",
            "Camping Lantern LED",
            "Hiking Backpack 40L",
            "Running Armband Phone",
            "Exercise Ball 65cm",
            "Jump Rope Speed",
            
            # Beauty & Health
            "Face Mask Moisturizing",
            "Hair Brush Detangling",
            "Essential Oil Set",
            "Massage Gun Electric",
            "Nail File Glass",
            "Lip Balm Natural",
            "Hand Cream Organic",
            "Soap Bar Handmade",
            
            # Automotive
            "Car Phone Mount",
            "USB Car Charger",
            "Air Freshener Bamboo",
            "Car Seat Cover",
            "Tire Pressure Gauge",
            "Car Cleaning Kit",
            "Dashboard Camera HD",
            "Emergency Kit Auto",
            
            # Tools & Hardware
            "Screwdriver Set Multi",
            "LED Flashlight Rechargeable",
            "Measuring Tape 25ft",
            "Work Gloves Safety",
            "Drill Bits Set",
            "Tool Bag Canvas",
            "Level Magnetic",
            "Utility Knife Sharp"
        ]

        imported_products = []
        available_names = product_names.copy()
        
        for i in range(min(count, len(available_names))):
            # Pick a random product name and remove it to avoid duplicates
            name = random.choice(available_names)
            available_names.remove(name)
            
            product = self.generate_mock_product(
                name,
                category=category,
                created_by=created_by
            )
            if product:
                imported_products.append(product)

        logger.info(f"Generated {len(imported_products)} mock products")
        return imported_products


class MockJumiaScraper:
    """Mock Jumia scraper for testing purposes"""

    def __init__(self):
        # Jumia category mappings for mock generation
        self.categories = {
            'electronics': 'Electronics',
            'fashion': 'Fashion',
            'phones-tablets': 'Phones & Tablets',
            'home-office': 'Home & Office',
            'beauty-health': 'Beauty & Health',
            'kids-babies': 'Kids & Babies',
            'sports-fitness': 'Sports & Fitness',
            'automobile': 'Automobile',
            'books-games': 'Books & Games',
            'garden-outdoor': 'Garden & Outdoor',
            'food-drinks': 'Food & Drinks',
            'services': 'Services'
        }
        
        # Sample products for each category
        self.sample_products = {
            'electronics': [
                'LED Smart TV 43"', 'Bluetooth Wireless Speaker', 'Gaming Mouse RGB',
                'USB-C Power Bank 20000mAh', 'Wireless Earbuds Pro', 'Smart Home Camera',
                'Electric Kettle 1.7L', 'Air Fryer Digital', 'Microwave Oven 20L'
            ],
            'fashion': [
                'Cotton T-Shirt Men', 'Women Summer Dress', 'Leather Jacket Brown',
                'Running Sneakers', 'Designer Handbag', 'Casual Jeans Blue',
                'Evening Gown Black', 'Sports Polo Shirt', 'Winter Coat Warm'
            ],
            'phones-tablets': [
                'Smartphone Android 128GB', 'iPhone 13 Pro Max', 'Samsung Galaxy Tab',
                'iPad Air 10.9"', 'Phone Case Protective', 'Screen Protector Tempered Glass',
                'Wireless Charger Fast', 'Phone Stand Adjustable', 'Bluetooth Headset'
            ],
            'home-office': [
                'Office Chair Ergonomic', 'Standing Desk Adjustable', 'LED Desk Lamp',
                'Wireless Keyboard Mouse', 'Monitor Stand Aluminum', 'Filing Cabinet Wood',
                'Whiteboard Magnetic', 'Desk Organizer Set', 'Table Lamp Modern'
            ],
            'beauty-health': [
                'Face Cream Anti-Aging', 'Vitamin C Serum', 'Hair Dryer Professional',
                'Electric Toothbrush', 'Massage Oil Relaxing', 'Skincare Set Complete',
                'Perfume Unisex 100ml', 'Hair Straightener Ceramic', 'Body Lotion Moisturizing'
            ],
            'kids-babies': [
                'Baby Stroller Lightweight', 'Educational Toys Set', 'Kids Bicycle 16"',
                'Baby Feeding Bottle', 'Children Backpack', 'Toy Car Remote Control',
                'Baby Monitor Video', 'Kids Puzzle Educational', 'Baby Clothes Set'
            ],
            'sports-fitness': [
                'Yoga Mat Non-Slip', 'Dumbbells Set 20kg', 'Fitness Tracker Watch',
                'Running Shoes Men', 'Gym Bag Large', 'Protein Shaker Bottle',
                'Resistance Bands Set', 'Basketball Official Size', 'Football Soccer Ball'
            ],
            'automobile': [
                'Car Phone Mount', 'Dash Cam HD 1080p', 'Car Charger Dual USB',
                'Tire Pressure Gauge', 'Car Air Freshener', 'Jump Starter Portable',
                'Car Seat Covers', 'LED Car Lights', 'Car Vacuum Cleaner'
            ],
            'books-games': [
                'Fiction Novel Bestseller', 'Educational Book Kids', 'Board Game Strategy',
                'Puzzle 1000 Pieces', 'Gaming Controller Wireless', 'Children Story Book',
                'Cookbook Healthy Recipes', 'Video Game Latest Release', 'Art Coloring Book'
            ],
            'garden-outdoor': [
                'Garden Tools Set', 'Outdoor Tent 4 Person', 'BBQ Grill Portable',
                'Plant Pots Ceramic', 'Garden Hose 50ft', 'Outdoor Chair Folding',
                'Solar Garden Lights', 'Camping Chair Lightweight', 'Watering Can 2L'
            ],
            'food-drinks': [
                'Organic Rice 5kg', 'Premium Coffee Beans', 'Natural Honey Pure',
                'Cooking Oil Sunflower', 'Breakfast Cereal Healthy', 'Green Tea Organic',
                'Pasta Whole Wheat', 'Spices Mix Set', 'Energy Drink Sugar-Free'
            ],
            'services': [
                'Home Cleaning Service', 'Phone Repair Service', 'Delivery Service',
                'Installation Service', 'Maintenance Service', 'Consultation Service',
                'Training Course Online', 'Technical Support', 'Design Service'
            ]
        }

    def generate_by_keyword(self, keyword, count, category=None, created_by=None):
        """Generate mock products based on keyword"""
        products = []
        keyword_lower = keyword.lower()
        
        # Find products that match the keyword
        matching_products = []
        for cat_products in self.sample_products.values():
            for product_name in cat_products:
                if any(word in product_name.lower() for word in keyword_lower.split()):
                    matching_products.append(product_name)
        
        # If no matches, create generic products based on keyword
        if not matching_products:
            for i in range(count):
                matching_products.append(f'{keyword.title()} Product {i+1}')
        
        # Generate requested number of products
        import random
        selected_products = random.sample(matching_products, min(count, len(matching_products)))
        
        for product_name in selected_products:
            product = self._generate_mock_product(
                product_name, 
                category or self._get_default_category(),
                created_by
            )
            if product:
                products.append(product)
                
        return products

    def generate_by_category(self, category_name, count, category=None, created_by=None):
        """Generate mock products for a specific category"""
        products = []
        
        if category_name not in self.sample_products:
            # Create generic products for unknown categories
            for i in range(count):
                product_name = f'{category_name.replace("-", " ").title()} Product {i+1}'
                product = self._generate_mock_product(
                    product_name,
                    category or self._get_default_category(), 
                    created_by
                )
                if product:
                    products.append(product)
            return products
        
        # Get products for the category
        category_products = self.sample_products[category_name]
        import random
        
        # If we need more products than available, repeat with variations
        selected_products = []
        for i in range(count):
            base_product = random.choice(category_products)
            if i < len(category_products):
                selected_products.append(base_product)
            else:
                # Add variation
                variations = ['Premium', 'Pro', 'Deluxe', 'Standard', 'Basic', 'Plus']
                variation = random.choice(variations)
                selected_products.append(f'{variation} {base_product}')
        
        for product_name in selected_products:
            product = self._generate_mock_product(
                product_name,
                category or self._get_default_category(),
                created_by
            )
            if product:
                products.append(product)
                
        return products

    def _generate_mock_product(self, name, category=None, created_by=None):
        """Generate a single mock Jumia product"""
        from decimal import Decimal
        import random

        try:
            # Generate unique slug
            base_slug = slugify(name)[:290]  # Leave room for counter
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            # Generate unique SKU
            sku = slugify(name)[:45]
            counter = 1
            while Product.objects.filter(sku=sku).exists():
                sku = f"{slugify(name)[:40]}-{counter}"
                counter += 1

            # Random pricing in GHS (Ghana Cedis)
            base_prices = [29.99, 49.99, 79.99, 99.99, 149.99, 199.99, 299.99, 499.99, 799.99]
            base_price = Decimal(str(random.choice(base_prices)))

            product = Product.objects.create(
                name=name,
                slug=slug,
                description=f"High-quality {name} imported from Jumia Ghana. "
                           f"Perfect for daily use with excellent features and durability. "
                           f"Fast delivery available across Ghana.",
                short_description=f"Quality {name} from Jumia Ghana",
                category=category or self._get_default_category(),
                base_price=base_price,
                discount_percentage=Decimal(str(random.choice([0, 5, 10, 15, 20, 25]))),
                sku=sku,
                brand=random.choice(['Samsung', 'Apple', 'LG', 'Sony', 'Philips', 'Generic', 'Jumia Brand']),
                is_active=True,
                is_featured=random.choice([True, False]),
                created_by=created_by
            )

            # Create default variant
            ProductVariant.objects.create(
                product=product,
                sku=f"{sku}-default",
                name="Standard",
                stock_quantity=random.randint(10, 100),
                is_active=True
            )

            logger.info(f"Generated mock Jumia product: {product.name}")
            return product

        except Exception as e:
            logger.error(f"Error generating mock Jumia product: {str(e)}")
            return None

    def _get_default_category(self):
        """Get or create default category for mock Jumia products"""
        category, created = Category.objects.get_or_create(
            slug='jumia-imported',
            defaults={
                'name': 'Jumia Imported Products',
                'description': 'Products imported from Jumia Ghana marketplace'
            }
        )
        return category

    def generate_category_products(self, category_name, count=20, db_category=None, created_by=None):
        """Generate products for a specific category (alias for generate_by_category)"""
        return self.generate_by_category(
            category_name,
            count, 
            category=db_category,
            created_by=created_by
        )
