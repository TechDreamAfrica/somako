"""
Management command to populate sample shops and products
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from shop.models import Shop, Product, ProductVariant, ProductImage, Category
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate sample shops and products'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample shops and products...')
        
        # Get or create a default owner
        owner = User.objects.filter(is_superuser=True).first()
        if not owner:
            owner = User.objects.first()
        
        if not owner:
            self.stdout.write(self.style.ERROR('No user found. Please create a user first.'))
            return

        # Create categories
        categories_data = [
            {'name': 'Electronics', 'description': 'Electronic devices and gadgets'},
            {'name': 'Fashion', 'description': 'Clothing, shoes, and accessories'},
            {'name': 'Home & Living', 'description': 'Furniture, decor, and home essentials'},
            {'name': 'Beauty & Personal Care', 'description': 'Skincare, cosmetics, and personal care products'},
            {'name': 'Sports & Outdoors', 'description': 'Sports equipment and outdoor gear'},
            {'name': 'Books & Stationery', 'description': 'Books, office supplies, and stationery'},
            {'name': 'Groceries', 'description': 'Food items and household essentials'},
            {'name': 'Toys & Games', 'description': 'Toys, games, and entertainment'},
        ]
        
        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            categories[cat_data['name']] = category
            if created:
                self.stdout.write(f'  Created category: {category.name}')

        # Shop data
        shops_data = [
            {
                'name': 'TechHub Ghana',
                'description': 'Your one-stop shop for the latest electronics and gadgets. We offer genuine products with warranty and excellent customer service. From smartphones to laptops, we have everything you need.',
                'phone': '+233 24 111 2222',
                'email': 'info@techhubgh.com',
                'address': '25 Oxford Street, Osu',
                'city': 'Accra',
                'state': 'Greater Accra',
                'business_type': 'Electronics',
                'is_verified': True,
                'is_featured': True,
                'delivery_fee': Decimal('15.00'),
                'estimated_delivery_time': 60,
                'average_rating': Decimal('4.7'),
                'total_reviews': 256,
            },
            {
                'name': 'Fashion Forward',
                'description': 'Trendy fashion for the modern Ghanaian. We bring you the latest styles from around the world at affordable prices. Quality clothing for men, women, and children.',
                'phone': '+233 30 222 3333',
                'email': 'hello@fashionforward.gh',
                'address': '10 Ring Road Central',
                'city': 'Accra',
                'state': 'Greater Accra',
                'business_type': 'Fashion',
                'is_verified': True,
                'is_featured': True,
                'delivery_fee': Decimal('10.00'),
                'estimated_delivery_time': 45,
                'average_rating': Decimal('4.5'),
                'total_reviews': 189,
            },
            {
                'name': 'Home Essentials Plus',
                'description': 'Transform your living space with our premium home essentials. From furniture to decor, we have everything to make your house a home. Quality products at competitive prices.',
                'phone': '+233 54 333 4444',
                'email': 'sales@homeessentials.gh',
                'address': '15 Liberation Road',
                'city': 'Kumasi',
                'state': 'Ashanti',
                'business_type': 'Home & Living',
                'is_verified': True,
                'is_featured': False,
                'delivery_fee': Decimal('25.00'),
                'estimated_delivery_time': 90,
                'average_rating': Decimal('4.3'),
                'total_reviews': 124,
            },
            {
                'name': 'Beauty Box Ghana',
                'description': 'Premium beauty and skincare products for every skin type. We stock local and international brands to help you look and feel your best. Free beauty consultations available.',
                'phone': '+233 20 444 5555',
                'email': 'care@beautyboxgh.com',
                'address': '5 Independence Avenue',
                'city': 'Tema',
                'state': 'Greater Accra',
                'business_type': 'Beauty & Personal Care',
                'is_verified': True,
                'is_featured': True,
                'delivery_fee': Decimal('8.00'),
                'estimated_delivery_time': 40,
                'average_rating': Decimal('4.8'),
                'total_reviews': 312,
            },
            {
                'name': 'Sports Central',
                'description': 'Get fit with our wide range of sports equipment and outdoor gear. Whether you\'re a professional athlete or weekend warrior, we have the gear you need to excel.',
                'phone': '+233 26 555 6666',
                'email': 'contact@sportscentral.gh',
                'address': '20 Market Circle',
                'city': 'Takoradi',
                'state': 'Western',
                'business_type': 'Sports & Outdoors',
                'is_verified': True,
                'is_featured': False,
                'delivery_fee': Decimal('20.00'),
                'estimated_delivery_time': 75,
                'average_rating': Decimal('4.4'),
                'total_reviews': 87,
            },
        ]

        # Products data per shop
        products_data = [
            # Shop 1 - TechHub Ghana (Electronics)
            [
                {
                    'name': 'Samsung Galaxy S24 Ultra',
                    'category': 'Electronics',
                    'description': 'The ultimate smartphone experience with AI-powered camera, S Pen support, and powerful performance. Features a stunning 6.8" Dynamic AMOLED display.',
                    'short_description': 'Flagship smartphone with AI camera and S Pen',
                    'base_price': Decimal('8500.00'),
                    'discount_percentage': Decimal('5.00'),
                    'brand': 'Samsung',
                    'is_featured': True,
                    'variants': [
                        {'name': '256GB - Titanium Black', 'size': '256GB', 'color': 'Titanium Black', 'stock_quantity': 25},
                        {'name': '512GB - Titanium Gray', 'size': '512GB', 'color': 'Titanium Gray', 'stock_quantity': 15},
                    ]
                },
                {
                    'name': 'MacBook Air M3 15"',
                    'category': 'Electronics',
                    'description': 'Apple\'s most popular laptop, now with the M3 chip. Up to 18 hours of battery life, stunning Liquid Retina display, and fanless design for silent operation.',
                    'short_description': 'Powerful, portable laptop with M3 chip',
                    'base_price': Decimal('12000.00'),
                    'discount_percentage': Decimal('0.00'),
                    'brand': 'Apple',
                    'is_featured': True,
                    'variants': [
                        {'name': '8GB/256GB - Midnight', 'size': '256GB', 'color': 'Midnight', 'stock_quantity': 10},
                        {'name': '16GB/512GB - Space Gray', 'size': '512GB', 'color': 'Space Gray', 'stock_quantity': 8},
                    ]
                },
                {
                    'name': 'Sony WH-1000XM5 Headphones',
                    'category': 'Electronics',
                    'description': 'Industry-leading noise cancellation with Auto NC Optimizer. 30-hour battery life, multipoint connection, and crystal clear hands-free calling.',
                    'short_description': 'Premium noise-canceling wireless headphones',
                    'base_price': Decimal('1800.00'),
                    'discount_percentage': Decimal('10.00'),
                    'brand': 'Sony',
                    'is_featured': False,
                    'variants': [
                        {'name': 'Black', 'color': 'Black', 'stock_quantity': 30},
                        {'name': 'Silver', 'color': 'Silver', 'stock_quantity': 20},
                    ]
                },
                {
                    'name': 'iPad Pro 12.9" M4',
                    'category': 'Electronics',
                    'description': 'The most powerful iPad ever with the M4 chip, stunning Tandem OLED display, and Apple Pencil Pro support. Perfect for creative professionals.',
                    'short_description': 'Professional tablet with M4 chip and OLED display',
                    'base_price': Decimal('9500.00'),
                    'discount_percentage': Decimal('0.00'),
                    'brand': 'Apple',
                    'is_featured': True,
                    'variants': [
                        {'name': '256GB - Space Black', 'size': '256GB', 'color': 'Space Black', 'stock_quantity': 12},
                        {'name': '512GB - Silver', 'size': '512GB', 'color': 'Silver', 'stock_quantity': 8},
                    ]
                },
                {
                    'name': 'JBL Flip 6 Portable Speaker',
                    'category': 'Electronics',
                    'description': 'Powerful JBL Original Pro Sound with punchy bass. IP67 waterproof and dustproof, 12 hours playtime. Perfect for outdoor adventures.',
                    'short_description': 'Waterproof portable Bluetooth speaker',
                    'base_price': Decimal('650.00'),
                    'discount_percentage': Decimal('15.00'),
                    'brand': 'JBL',
                    'is_featured': False,
                    'variants': [
                        {'name': 'Black', 'color': 'Black', 'stock_quantity': 50},
                        {'name': 'Blue', 'color': 'Blue', 'stock_quantity': 35},
                        {'name': 'Red', 'color': 'Red', 'stock_quantity': 25},
                    ]
                },
            ],
            # Shop 2 - Fashion Forward (Fashion)
            [
                {
                    'name': 'Men\'s Premium African Print Shirt',
                    'category': 'Fashion',
                    'description': 'Handcrafted African print shirt made from 100% cotton. Features vibrant traditional patterns with modern tailoring for a perfect fit.',
                    'short_description': 'Traditional African print casual shirt',
                    'base_price': Decimal('250.00'),
                    'discount_percentage': Decimal('0.00'),
                    'brand': 'Kente King',
                    'is_featured': True,
                    'variants': [
                        {'name': 'Small - Blue Pattern', 'size': 'S', 'color': 'Blue Pattern', 'stock_quantity': 20},
                        {'name': 'Medium - Blue Pattern', 'size': 'M', 'color': 'Blue Pattern', 'stock_quantity': 35},
                        {'name': 'Large - Blue Pattern', 'size': 'L', 'color': 'Blue Pattern', 'stock_quantity': 30},
                        {'name': 'XL - Gold Pattern', 'size': 'XL', 'color': 'Gold Pattern', 'stock_quantity': 25},
                    ]
                },
                {
                    'name': 'Women\'s Ankara Maxi Dress',
                    'category': 'Fashion',
                    'description': 'Elegant maxi dress featuring beautiful Ankara fabric. Perfect for special occasions and everyday glamour. Includes matching headwrap.',
                    'short_description': 'Beautiful Ankara maxi dress with headwrap',
                    'base_price': Decimal('450.00'),
                    'discount_percentage': Decimal('20.00'),
                    'brand': 'AfroChic',
                    'is_featured': True,
                    'variants': [
                        {'name': 'Size 8 - Sunset Orange', 'size': '8', 'color': 'Sunset Orange', 'stock_quantity': 15},
                        {'name': 'Size 10 - Sunset Orange', 'size': '10', 'color': 'Sunset Orange', 'stock_quantity': 20},
                        {'name': 'Size 12 - Royal Blue', 'size': '12', 'color': 'Royal Blue', 'stock_quantity': 18},
                    ]
                },
                {
                    'name': 'Unisex Leather Sandals',
                    'category': 'Fashion',
                    'description': 'Handmade genuine leather sandals crafted by local artisans. Comfortable, durable, and perfect for the African climate.',
                    'short_description': 'Handcrafted genuine leather sandals',
                    'base_price': Decimal('180.00'),
                    'discount_percentage': Decimal('0.00'),
                    'brand': 'SoleAfrica',
                    'is_featured': False,
                    'variants': [
                        {'name': 'Size 40 - Brown', 'size': '40', 'color': 'Brown', 'stock_quantity': 25},
                        {'name': 'Size 42 - Brown', 'size': '42', 'color': 'Brown', 'stock_quantity': 30},
                        {'name': 'Size 44 - Black', 'size': '44', 'color': 'Black', 'stock_quantity': 20},
                    ]
                },
                {
                    'name': 'Canvas Tote Bag - Tribal Print',
                    'category': 'Fashion',
                    'description': 'Eco-friendly canvas tote with authentic tribal print. Spacious interior with inner pocket. Perfect for shopping, beach, or everyday use.',
                    'short_description': 'Stylish eco-friendly canvas tote bag',
                    'base_price': Decimal('85.00'),
                    'discount_percentage': Decimal('10.00'),
                    'brand': 'GreenStyle',
                    'is_featured': False,
                    'variants': [
                        {'name': 'Earth Brown', 'color': 'Earth Brown', 'stock_quantity': 50},
                        {'name': 'Ocean Blue', 'color': 'Ocean Blue', 'stock_quantity': 40},
                    ]
                },
                {
                    'name': 'Men\'s Slim Fit Chinos',
                    'category': 'Fashion',
                    'description': 'Premium cotton chinos with stretch for comfort. Modern slim fit perfect for both casual and semi-formal occasions.',
                    'short_description': 'Comfortable slim fit cotton chinos',
                    'base_price': Decimal('220.00'),
                    'discount_percentage': Decimal('0.00'),
                    'brand': 'UrbanWear',
                    'is_featured': True,
                    'variants': [
                        {'name': 'Size 30 - Navy', 'size': '30', 'color': 'Navy', 'stock_quantity': 30},
                        {'name': 'Size 32 - Khaki', 'size': '32', 'color': 'Khaki', 'stock_quantity': 35},
                        {'name': 'Size 34 - Black', 'size': '34', 'color': 'Black', 'stock_quantity': 25},
                    ]
                },
            ],
            # Shop 3 - Home Essentials Plus (Home & Living)
            [
                {
                    'name': '3-Seater Fabric Sofa',
                    'category': 'Home & Living',
                    'description': 'Modern 3-seater sofa with premium fabric upholstery. Features high-density foam for maximum comfort and sturdy wooden frame.',
                    'short_description': 'Comfortable modern fabric sofa',
                    'base_price': Decimal('4500.00'),
                    'discount_percentage': Decimal('10.00'),
                    'brand': 'ComfortHome',
                    'is_featured': True,
                    'variants': [
                        {'name': 'Grey', 'color': 'Grey', 'stock_quantity': 8},
                        {'name': 'Navy Blue', 'color': 'Navy Blue', 'stock_quantity': 5},
                        {'name': 'Beige', 'color': 'Beige', 'stock_quantity': 6},
                    ]
                },
                {
                    'name': 'Wooden Dining Table Set (6 Chairs)',
                    'category': 'Home & Living',
                    'description': 'Solid mahogany dining set including table and 6 matching chairs. Classic design with modern touches. Perfect for family gatherings.',
                    'short_description': '6-seater mahogany dining set',
                    'base_price': Decimal('8500.00'),
                    'discount_percentage': Decimal('5.00'),
                    'brand': 'WoodCraft',
                    'is_featured': True,
                    'variants': [
                        {'name': 'Natural Finish', 'color': 'Natural', 'stock_quantity': 4},
                        {'name': 'Dark Walnut', 'color': 'Dark Walnut', 'stock_quantity': 3},
                    ]
                },
                {
                    'name': 'Premium Bed Sheet Set - King Size',
                    'category': 'Home & Living',
                    'description': '400 thread count Egyptian cotton bed sheet set. Includes fitted sheet, flat sheet, and 4 pillowcases. Luxuriously soft and breathable.',
                    'short_description': 'Egyptian cotton king size bed sheets',
                    'base_price': Decimal('650.00'),
                    'discount_percentage': Decimal('15.00'),
                    'brand': 'DreamSleep',
                    'is_featured': False,
                    'variants': [
                        {'name': 'White', 'color': 'White', 'stock_quantity': 30},
                        {'name': 'Sage Green', 'color': 'Sage Green', 'stock_quantity': 20},
                        {'name': 'Dusty Pink', 'color': 'Dusty Pink', 'stock_quantity': 15},
                    ]
                },
                {
                    'name': 'LED Ceiling Fan with Remote',
                    'category': 'Home & Living',
                    'description': '52-inch ceiling fan with integrated LED light. 3 speed settings, reversible motor, and remote control. Energy efficient and quiet operation.',
                    'short_description': 'Modern LED ceiling fan with remote',
                    'base_price': Decimal('850.00'),
                    'discount_percentage': Decimal('0.00'),
                    'brand': 'CoolBreeze',
                    'is_featured': False,
                    'variants': [
                        {'name': 'Matte Black', 'color': 'Matte Black', 'stock_quantity': 25},
                        {'name': 'White', 'color': 'White', 'stock_quantity': 20},
                    ]
                },
                {
                    'name': 'Decorative Wall Art Set (3 Pieces)',
                    'category': 'Home & Living',
                    'description': 'Set of 3 canvas prints featuring contemporary African art. Ready to hang with included hardware. Perfect for living room or bedroom.',
                    'short_description': '3-piece African contemporary wall art',
                    'base_price': Decimal('380.00'),
                    'discount_percentage': Decimal('20.00'),
                    'brand': 'ArtisanGH',
                    'is_featured': True,
                    'variants': [
                        {'name': 'Sunset Collection', 'color': 'Warm Tones', 'stock_quantity': 15},
                        {'name': 'Ocean Collection', 'color': 'Cool Tones', 'stock_quantity': 12},
                    ]
                },
            ],
            # Shop 4 - Beauty Box Ghana (Beauty & Personal Care)
            [
                {
                    'name': 'Shea Butter Body Lotion Set',
                    'category': 'Beauty & Personal Care',
                    'description': 'Natural shea butter body care set including body lotion, body butter, and hand cream. Made with pure Ghanaian shea butter. Deeply moisturizing.',
                    'short_description': '3-piece natural shea butter body care set',
                    'base_price': Decimal('185.00'),
                    'discount_percentage': Decimal('0.00'),
                    'brand': 'SheaGlow',
                    'is_featured': True,
                    'variants': [
                        {'name': 'Lavender Scent', 'color': 'Lavender', 'stock_quantity': 45},
                        {'name': 'Vanilla Scent', 'color': 'Vanilla', 'stock_quantity': 40},
                        {'name': 'Unscented', 'color': 'Natural', 'stock_quantity': 35},
                    ]
                },
                {
                    'name': 'Natural Hair Growth Oil',
                    'category': 'Beauty & Personal Care',
                    'description': 'Powerful blend of African oils for natural hair growth. Contains castor oil, black seed oil, and chebe powder. Stimulates growth and reduces breakage.',
                    'short_description': 'African hair growth oil blend',
                    'base_price': Decimal('120.00'),
                    'discount_percentage': Decimal('10.00'),
                    'brand': 'RootsNatural',
                    'is_featured': True,
                    'variants': [
                        {'name': '100ml', 'size': '100ml', 'stock_quantity': 60},
                        {'name': '250ml', 'size': '250ml', 'stock_quantity': 40},
                    ]
                },
                {
                    'name': 'Vitamin C Brightening Serum',
                    'category': 'Beauty & Personal Care',
                    'description': '20% Vitamin C serum with hyaluronic acid. Brightens skin, reduces dark spots, and boosts collagen production. Suitable for all skin types.',
                    'short_description': 'Skin brightening vitamin C serum',
                    'base_price': Decimal('280.00'),
                    'discount_percentage': Decimal('0.00'),
                    'brand': 'GlowSkin',
                    'is_featured': False,
                    'variants': [
                        {'name': '30ml', 'size': '30ml', 'stock_quantity': 50},
                    ]
                },
                {
                    'name': 'African Black Soap Bar (Pack of 3)',
                    'category': 'Beauty & Personal Care',
                    'description': 'Authentic African black soap from Ghana. Natural ingredients including plantain ash and cocoa pod ash. Gentle cleanser suitable for face and body.',
                    'short_description': 'Traditional African black soap 3-pack',
                    'base_price': Decimal('75.00'),
                    'discount_percentage': Decimal('20.00'),
                    'brand': 'PureSkin',
                    'is_featured': False,
                    'variants': [
                        {'name': 'Original', 'color': 'Original', 'stock_quantity': 100},
                        {'name': 'With Honey', 'color': 'Honey', 'stock_quantity': 80},
                    ]
                },
                {
                    'name': 'Complete Makeup Brush Set',
                    'category': 'Beauty & Personal Care',
                    'description': 'Professional 15-piece makeup brush set with synthetic bristles. Includes brushes for face, eyes, and lips. Comes with elegant leather pouch.',
                    'short_description': '15-piece professional makeup brush set',
                    'base_price': Decimal('350.00'),
                    'discount_percentage': Decimal('15.00'),
                    'brand': 'ProBeauty',
                    'is_featured': True,
                    'variants': [
                        {'name': 'Rose Gold', 'color': 'Rose Gold', 'stock_quantity': 30},
                        {'name': 'Classic Black', 'color': 'Black', 'stock_quantity': 25},
                    ]
                },
            ],
            # Shop 5 - Sports Central (Sports & Outdoors)
            [
                {
                    'name': 'Professional Football Boots',
                    'category': 'Sports & Outdoors',
                    'description': 'High-performance football boots with textured upper for better ball control. Lightweight design with excellent grip on grass and artificial turf.',
                    'short_description': 'Pro-level football boots for all surfaces',
                    'base_price': Decimal('580.00'),
                    'discount_percentage': Decimal('10.00'),
                    'brand': 'StrikeForce',
                    'is_featured': True,
                    'variants': [
                        {'name': 'Size 42 - Black/Gold', 'size': '42', 'color': 'Black/Gold', 'stock_quantity': 15},
                        {'name': 'Size 43 - Black/Gold', 'size': '43', 'color': 'Black/Gold', 'stock_quantity': 20},
                        {'name': 'Size 44 - White/Blue', 'size': '44', 'color': 'White/Blue', 'stock_quantity': 12},
                    ]
                },
                {
                    'name': 'Yoga Mat with Carrying Strap',
                    'category': 'Sports & Outdoors',
                    'description': 'Premium 6mm thick yoga mat with non-slip surface. Made from eco-friendly TPE material. Includes carrying strap and cleaning spray.',
                    'short_description': 'Eco-friendly non-slip yoga mat',
                    'base_price': Decimal('150.00'),
                    'discount_percentage': Decimal('0.00'),
                    'brand': 'ZenFit',
                    'is_featured': False,
                    'variants': [
                        {'name': 'Purple', 'color': 'Purple', 'stock_quantity': 40},
                        {'name': 'Teal', 'color': 'Teal', 'stock_quantity': 35},
                        {'name': 'Black', 'color': 'Black', 'stock_quantity': 30},
                    ]
                },
                {
                    'name': 'Adjustable Dumbbell Set (2-24kg)',
                    'category': 'Sports & Outdoors',
                    'description': 'Space-saving adjustable dumbbells. Quick-change weight system from 2kg to 24kg. Compact design perfect for home gyms.',
                    'short_description': 'Adjustable home gym dumbbells',
                    'base_price': Decimal('2800.00'),
                    'discount_percentage': Decimal('5.00'),
                    'brand': 'PowerLift',
                    'is_featured': True,
                    'variants': [
                        {'name': 'Single (2-24kg)', 'size': 'Single', 'stock_quantity': 20},
                        {'name': 'Pair (2-24kg each)', 'size': 'Pair', 'stock_quantity': 15},
                    ]
                },
                {
                    'name': 'Running Shoes - Marathon Edition',
                    'category': 'Sports & Outdoors',
                    'description': 'Lightweight running shoes designed for long-distance running. Carbon fiber plate for energy return, breathable mesh upper, and cushioned midsole.',
                    'short_description': 'Professional marathon running shoes',
                    'base_price': Decimal('750.00'),
                    'discount_percentage': Decimal('0.00'),
                    'brand': 'RunElite',
                    'is_featured': True,
                    'variants': [
                        {'name': 'Size 41 - Neon Green', 'size': '41', 'color': 'Neon Green', 'stock_quantity': 18},
                        {'name': 'Size 42 - Black/Red', 'size': '42', 'color': 'Black/Red', 'stock_quantity': 22},
                        {'name': 'Size 43 - Blue/White', 'size': '43', 'color': 'Blue/White', 'stock_quantity': 20},
                    ]
                },
                {
                    'name': 'Camping Tent (4-Person)',
                    'category': 'Sports & Outdoors',
                    'description': 'Waterproof 4-person dome tent with rainfly. Easy setup with color-coded poles. Includes stakes, guy lines, and carrying bag.',
                    'short_description': 'Waterproof 4-person camping tent',
                    'base_price': Decimal('680.00'),
                    'discount_percentage': Decimal('15.00'),
                    'brand': 'OutdoorPro',
                    'is_featured': False,
                    'variants': [
                        {'name': 'Green', 'color': 'Green', 'stock_quantity': 15},
                        {'name': 'Orange', 'color': 'Orange', 'stock_quantity': 10},
                    ]
                },
            ],
        ]

        # Create shops and their products
        for i, shop_data in enumerate(shops_data):
            shop, created = Shop.objects.get_or_create(
                name=shop_data['name'],
                defaults={
                    'owner': owner,
                    'description': shop_data['description'],
                    'phone': shop_data['phone'],
                    'email': shop_data['email'],
                    'address': shop_data['address'],
                    'city': shop_data['city'],
                    'state': shop_data['state'],
                    'business_type': shop_data.get('business_type', ''),
                    'is_verified': shop_data.get('is_verified', True),
                    'is_featured': shop_data.get('is_featured', False),
                    'delivery_fee': shop_data.get('delivery_fee', Decimal('10.00')),
                    'estimated_delivery_time': shop_data.get('estimated_delivery_time', 60),
                    'average_rating': shop_data.get('average_rating', Decimal('4.0')),
                    'total_reviews': shop_data.get('total_reviews', 0),
                    'status': 'active',
                    'delivery_available': True,
                }
            )
            
            if created:
                self.stdout.write(f'Created shop: {shop.name}')
            else:
                self.stdout.write(f'Shop already exists: {shop.name}')

            # Create products for this shop
            for prod_data in products_data[i]:
                category = categories.get(prod_data['category'])
                if not category:
                    self.stdout.write(self.style.WARNING(f"Category not found: {prod_data['category']}"))
                    continue

                # Generate unique SKU
                import uuid
                sku = f"{shop.slug[:3].upper()}-{uuid.uuid4().hex[:8].upper()}"

                product, prod_created = Product.objects.get_or_create(
                    name=prod_data['name'],
                    shop=shop,
                    defaults={
                        'category': category,
                        'description': prod_data['description'],
                        'short_description': prod_data.get('short_description', ''),
                        'base_price': prod_data['base_price'],
                        'discount_percentage': prod_data.get('discount_percentage', Decimal('0.00')),
                        'brand': prod_data.get('brand', ''),
                        'sku': sku,
                        'is_featured': prod_data.get('is_featured', False),
                        'is_active': True,
                        'created_by': owner,
                    }
                )
                
                if prod_created:
                    self.stdout.write(f'  - Created product: {product.name}')
                    
                    # Create variants
                    for var_data in prod_data.get('variants', []):
                        var_sku = f"{sku}-{uuid.uuid4().hex[:4].upper()}"
                        ProductVariant.objects.create(
                            product=product,
                            sku=var_sku,
                            name=var_data['name'],
                            size=var_data.get('size', ''),
                            color=var_data.get('color', ''),
                            stock_quantity=var_data.get('stock_quantity', 10),
                            is_active=True,
                        )

        self.stdout.write(self.style.SUCCESS('\nSuccessfully populated shops and products!'))
        self.stdout.write(f'Total shops: {Shop.objects.count()}')
        self.stdout.write(f'Total products: {Product.objects.count()}')
        self.stdout.write(f'Total variants: {ProductVariant.objects.count()}')
