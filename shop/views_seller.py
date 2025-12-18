"""
CRUD views for Sellers to manage Products
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Product, ProductImage
from .forms import ProductForm, ProductImageForm


@login_required
def product_list(request):
    """List all products owned by the logged-in seller"""
    products = Product.objects.filter(created_by=request.user).order_by('-created_at')
    context = {
        'products': products,
        'total_products': products.count(),
        'active_products': products.filter(is_active=True).count(),
    }
    return render(request, 'shop/seller/product_list.html', context)


@login_required
def product_create(request):
    """Create a new product"""
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            messages.success(request, 'Product created successfully!')
            return redirect('shop:product_detail', pk=product.pk)
    else:
        form = ProductForm()
    return render(request, 'shop/seller/product_form.html', {'form': form, 'action': 'Create'})


@login_required
def product_detail(request, pk):
    """View product details"""
    product = get_object_or_404(Product, pk=pk, created_by=request.user)
    images = product.images.all()
    return render(request, 'shop/seller/product_detail.html', {'product': product, 'images': images})


@login_required
def product_update(request, pk):
    """Update an existing product"""
    product = get_object_or_404(Product, pk=pk, created_by=request.user)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('shop:product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product)
    return render(request, 'shop/seller/product_form.html', {'form': form, 'product': product, 'action': 'Update'})


@login_required
def product_delete(request, pk):
    """Delete a product"""
    product = get_object_or_404(Product, pk=pk, created_by=request.user)
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Product "{product_name}" deleted successfully!')
        return redirect('shop:product_list')
    return render(request, 'shop/seller/product_confirm_delete.html', {'product': product})


@login_required
def product_toggle_active(request, pk):
    """Toggle product active status"""
    product = get_object_or_404(Product, pk=pk, created_by=request.user)
    product.is_active = not product.is_active
    product.save()
    status = 'active' if product.is_active else 'inactive'
    messages.success(request, f'Product marked as {status}!')
    return redirect('shop:product_detail', pk=product.pk)


@login_required
def product_image_add(request, product_pk):
    """Add images to a product"""
    product = get_object_or_404(Product, pk=product_pk, seller=request.user)
    if request.method == 'POST':
        form = ProductImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.product = product
            image.save()
            messages.success(request, 'Image added successfully!')
            return redirect('shop:product_detail', pk=product.pk)
    else:
        form = ProductImageForm()
    return render(request, 'shop/seller/product_image_form.html', {'form': form, 'product': product})


@login_required
def product_image_delete(request, pk):
    """Delete a product image"""
    image = get_object_or_404(ProductImage, pk=pk, product__created_by=request.user)
    product_pk = image.product.pk
    if request.method == 'POST':
        image.delete()
        messages.success(request, 'Image deleted successfully!')
        return redirect('shop:product_detail', pk=product_pk)
    return render(request, 'shop/seller/product_image_confirm_delete.html', {'image': image, 'product': image.product})
