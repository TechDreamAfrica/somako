"""
Management command to populate categories for all apps that need them.
Usage: python manage.py populate_categories
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

# Import all category models
from rent.models import PropertyCategory, EquipmentCategory
from shop.models import Category as ShopCategory
from pharmacy.models import MedicineCategory
from food.models import FoodCategory


class Command(BaseCommand):
    help = 'Populate categories for all apps (rent, shop, food, pharmacy)'

    def generate_unique_slug(self, model_class, name, parent=None):
        """Generate a unique slug for a category"""
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        
        # For shop categories, slugs must be globally unique
        while model_class.objects.filter(slug=slug).exists():
            counter += 1
            slug = f"{base_slug}-{counter}"
        
        return slug

    def add_arguments(self, parser):
        parser.add_argument(
            '--app',
            type=str,
            choices=['rent', 'shop', 'food', 'pharmacy', 'all'],
            default='all',
            help='Specify which app categories to populate (default: all)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing categories before populating'
        )

    def handle(self, *args, **options):
        app = options['app']
        clear = options['clear']

        self.stdout.write(
            self.style.SUCCESS('Starting category population...')
        )

        with transaction.atomic():
            if app == 'all' or app == 'rent':
                self.populate_rent_categories(clear)
            
            if app == 'all' or app == 'shop':
                self.populate_shop_categories(clear)
                
            if app == 'all' or app == 'food':
                self.populate_food_categories(clear)
                
            if app == 'all' or app == 'pharmacy':
                self.populate_pharmacy_categories(clear)

        self.stdout.write(
            self.style.SUCCESS('✅ Category population completed successfully!')
        )

    def populate_rent_categories(self, clear=False):
        """Populate property and equipment categories for rent app"""
        self.stdout.write('📍 Populating rent categories...')
        
        if clear:
            PropertyCategory.objects.all().delete()
            EquipmentCategory.objects.all().delete()
            self.stdout.write('  Cleared existing rent categories')

        # Property Categories
        property_categories = [
            {
                'name': 'Houses',
                'description': 'Single-family homes, duplexes, and townhouses for rent',
                'icon': 'fas fa-home'
            },
            {
                'name': 'Apartments',
                'description': 'Studio, 1BR, 2BR+ apartments and condominiums',
                'icon': 'fas fa-building'
            },
            {
                'name': 'Office Spaces',
                'description': 'Commercial office spaces and coworking areas',
                'icon': 'fas fa-briefcase'
            },
            {
                'name': 'Retail Spaces',
                'description': 'Shops, stores, and commercial retail spaces',
                'icon': 'fas fa-store'
            },
            {
                'name': 'Warehouses',
                'description': 'Storage facilities and industrial warehouses',
                'icon': 'fas fa-warehouse'
            },
            {
                'name': 'Land',
                'description': 'Plots of land for various purposes',
                'icon': 'fas fa-map'
            },
            {
                'name': 'Event Venues',
                'description': 'Halls, conference rooms, and event spaces',
                'icon': 'fas fa-calendar'
            },
            {
                'name': 'Vacation Rentals',
                'description': 'Short-term holiday and vacation properties',
                'icon': 'fas fa-umbrella-beach'
            }
        ]

        for cat_data in property_categories:
            category, created = PropertyCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'icon': cat_data['icon']
                }
            )
            if created:
                self.stdout.write(f'  ✓ Created property category: {category.name}')

        # Equipment Categories
        equipment_categories = [
            {
                'name': 'Construction Equipment',
                'description': 'Power tools, hand tools, and construction equipment',
                'icon': 'fas fa-tools'
            },
            {
                'name': 'Vehicle Rentals',
                'description': 'Cars, trucks, motorcycles, and other vehicles',
                'icon': 'fas fa-car'
            },
            {
                'name': 'AV Equipment',
                'description': 'Computers, cameras, audio equipment, and gadgets',
                'icon': 'fas fa-laptop'
            },
            {
                'name': 'Event Equipment',
                'description': 'Tents, sound systems, decorations, and party supplies',
                'icon': 'fas fa-music'
            },
            {
                'name': 'Sports Rentals',
                'description': 'Bicycles, gym equipment, and sporting goods',
                'icon': 'fas fa-dumbbell'
            },
            {
                'name': 'Garden Equipment',
                'description': 'Lawn mowers, outdoor furniture, and gardening tools',
                'icon': 'fas fa-seedling'
            },
            {
                'name': 'Kitchen Equipment',
                'description': 'Commercial kitchen equipment and appliances',
                'icon': 'fas fa-utensils'
            },
            {
                'name': 'Furniture Rental',
                'description': 'Temporary furniture for events and offices',
                'icon': 'fas fa-couch'
            }
        ]

        for cat_data in equipment_categories:
            category, created = EquipmentCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'icon': cat_data['icon']
                }
            )
            if created:
                self.stdout.write(f'  ✓ Created equipment category: {category.name}')

    def populate_shop_categories(self, clear=False):
        """Populate product categories for shop app with hierarchical structure"""
        self.stdout.write('🛒 Populating shop categories...')
        
        if clear:
            ShopCategory.objects.all().delete()
            self.stdout.write('  Cleared existing shop categories')

        # Main categories with subcategories
        categories_data = {
            'Electronics': [
                'Smartphones & Tablets',
                'Computers & Laptops',
                'Audio & Headphones',
                'Cameras & Photography',
                'Gaming',
                'Smart Home',
                'Accessories'
            ],
            'Fashion': [
                'Men\'s Clothing',
                'Women\'s Clothing',
                'Shoes',
                'Bags & Accessories',
                'Jewelry & Watches',
                'Kids\' Clothing',
                'Sports & Activewear'
            ],
            'Home & Garden': [
                'Furniture',
                'Kitchen & Dining',
                'Bedding & Bath',
                'Home Decor',
                'Garden & Outdoor',
                'Tools & Hardware',
                'Storage & Organization'
            ],
            'Beauty & Health': [
                'Skincare',
                'Makeup & Cosmetics',
                'Hair Care',
                'Fragrances',
                'Health & Wellness',
                'Personal Care',
                'Fitness & Nutrition'
            ],
            'Sports & Outdoors': [
                'Exercise & Fitness',
                'Team Sports',
                'Outdoor Recreation',
                'Water Sports',
                'Cycling',
                'Running & Athletics',
                'Sports Accessories'
            ],
            'Books & Media': [
                'Books',
                'Movies & TV',
                'Music',
                'Video Games',
                'Educational Materials',
                'Magazines',
                'E-books & Audiobooks'
            ],
            'Toys & Games': [
                'Action Figures',
                'Board Games',
                'Educational Toys',
                'Electronic Toys',
                'Outdoor Play',
                'Baby & Toddler Toys',
                'Collectibles'
            ],
            'Automotive': [
                'Car Accessories',
                'Motorcycle Parts',
                'Tools & Equipment',
                'Car Care',
                'Electronics & GPS',
                'Tires & Wheels',
                'Interior Accessories'
            ]
        }

        for main_cat_name, subcategories in categories_data.items():
            # Create main category
            unique_slug = self.generate_unique_slug(ShopCategory, main_cat_name, parent=None)
            main_category, created = ShopCategory.objects.get_or_create(
                name=main_cat_name,
                parent=None,
                defaults={'slug': unique_slug}
            )
            if created:
                self.stdout.write(f'  ✓ Created main category: {main_category.name}')

            # Create subcategories
            for sub_cat_name in subcategories:
                unique_slug = self.generate_unique_slug(ShopCategory, sub_cat_name, parent=main_category)
                sub_category, created = ShopCategory.objects.get_or_create(
                    name=sub_cat_name,
                    parent=main_category,
                    defaults={'slug': unique_slug}
                )
                if created:
                    self.stdout.write(f'    ✓ Created subcategory: {sub_cat_name}')

    def populate_food_categories(self, clear=False):
        """Populate food categories"""
        self.stdout.write('🍽️ Populating food categories...')
        
        if clear:
            try:
                FoodCategory.objects.all().delete()
                self.stdout.write('  Cleared existing food categories')
            except:
                self.stdout.write('  Note: FoodCategory model may not exist yet')
                return

        food_categories = [
            {
                'name': 'Fast Food',
                'description': 'Quick service restaurants and fast food chains'
            },
            {
                'name': 'Local Cuisine',
                'description': 'Traditional Ghanaian and West African dishes'
            },
            {
                'name': 'International',
                'description': 'Chinese, Indian, Italian, and other international cuisines'
            },
            {
                'name': 'Beverages',
                'description': 'Soft drinks, juices, coffee, tea, and other beverages'
            },
            {
                'name': 'Healthy & Organic',
                'description': 'Healthy meals, organic food, and dietary options'
            },
            {
                'name': 'Desserts & Sweets',
                'description': 'Cakes, ice cream, pastries, and sweet treats'
            },
            {
                'name': 'Breakfast',
                'description': 'Morning meals and breakfast items'
            },
            {
                'name': 'Seafood',
                'description': 'Fresh fish, shrimp, crab, and other seafood dishes'
            },
            {
                'name': 'Vegetarian & Vegan',
                'description': 'Plant-based meals and vegetarian options'
            },
            {
                'name': 'Grilled & BBQ',
                'description': 'Grilled meats, kebabs, and barbecue dishes'
            }
        ]

        for cat_data in food_categories:
            try:
                category, created = FoodCategory.objects.get_or_create(
                    name=cat_data['name'],
                    defaults={'description': cat_data['description']}
                )
                if created:
                    self.stdout.write(f'  ✓ Created food category: {category.name}')
            except Exception as e:
                self.stdout.write(f'  ⚠️  Could not create food category {cat_data["name"]}: {e}')

    def populate_pharmacy_categories(self, clear=False):
        """Populate medicine categories for pharmacy app"""
        self.stdout.write('💊 Populating pharmacy categories...')
        
        if clear:
            MedicineCategory.objects.all().delete()
            self.stdout.write('  Cleared existing pharmacy categories')

        medicine_categories = [
            {
                'name': 'Pain Relief',
                'description': 'Pain relievers, anti-inflammatory drugs, and analgesics'
            },
            {
                'name': 'Antibiotics',
                'description': 'Prescription antibiotics and antimicrobial medications'
            },
            {
                'name': 'Vitamins & Supplements',
                'description': 'Daily vitamins, minerals, and nutritional supplements'
            },
            {
                'name': 'Cold & Flu',
                'description': 'Medications for cold, flu, cough, and respiratory issues'
            },
            {
                'name': 'Digestive Health',
                'description': 'Medications for stomach, digestive, and gastrointestinal issues'
            },
            {
                'name': 'Heart & Blood Pressure',
                'description': 'Cardiovascular medications and blood pressure treatments'
            },
            {
                'name': 'Diabetes Care',
                'description': 'Insulin, blood sugar monitors, and diabetes management'
            },
            {
                'name': 'Skin Care',
                'description': 'Topical creams, ointments, and dermatological treatments'
            },
            {
                'name': 'Eye & Ear Care',
                'description': 'Eye drops, ear drops, and optical care products'
            },
            {
                'name': 'Women\'s Health',
                'description': 'Contraceptives, pregnancy tests, and women-specific medications'
            },
            {
                'name': 'Children\'s Medicine',
                'description': 'Pediatric medications and child-safe formulations'
            },
            {
                'name': 'First Aid',
                'description': 'Bandages, antiseptics, and emergency medical supplies'
            },
            {
                'name': 'Allergy & Asthma',
                'description': 'Antihistamines, inhalers, and allergy relief medications'
            },
            {
                'name': 'Mental Health',
                'description': 'Antidepressants, anxiety medications, and mental health treatments'
            },
            {
                'name': 'Sexual Health',
                'description': 'Contraceptives, fertility products, and sexual wellness'
            }
        ]

        for cat_data in medicine_categories:
            category, created = MedicineCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'slug': slugify(cat_data['name'])
                }
            )
            if created:
                self.stdout.write(f'  ✓ Created medicine category: {category.name}')