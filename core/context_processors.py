"""
Context processors for making cart counts available in all templates
"""

def cart_counts(request):
    """
    Add cart item counts to template context for all apps
    """
    counts = {
        'food_cart_count': 0,
        'shop_cart_count': 0,
        'pharmacy_cart_count': 0,
    }

    if request.user.is_authenticated:
        try:
            # Food cart count
            from food.models import Cart as FoodCart
            food_cart = FoodCart.objects.filter(user=request.user).first()
            if food_cart:
                counts['food_cart_count'] = food_cart.get_item_count()
        except:
            pass

        try:
            # Shop cart count
            from shop.models import Cart as ShopCart
            shop_cart = ShopCart.objects.filter(user=request.user).first()
            if shop_cart:
                counts['shop_cart_count'] = shop_cart.items.count()
        except:
            pass

        try:
            # Pharmacy cart count
            from pharmacy.models import Cart as PharmacyCart
            pharmacy_cart = PharmacyCart.objects.filter(user=request.user).first()
            if pharmacy_cart:
                counts['pharmacy_cart_count'] = pharmacy_cart.items.count()
        except:
            pass

    # Total cart count
    counts['total_cart_count'] = counts['food_cart_count'] + counts['shop_cart_count'] + counts['pharmacy_cart_count']

    return counts
