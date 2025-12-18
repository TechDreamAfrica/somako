from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .notification_models import Notification, NotificationPreference


@login_required
def notifications_list(request):
    """View all notifications for the logged-in user"""
    notifications = Notification.objects.filter(
        user=request.user,
        channel='in_app'
    ).order_by('-created_at')

    # Separate unread and read notifications
    unread = notifications.filter(read_at__isnull=True)
    read = notifications.filter(read_at__isnull=False)[:50]  # Limit read to 50

    context = {
        'unread_notifications': unread,
        'read_notifications': read,
        'total_unread': unread.count(),
    }

    return render(request, 'accounts/notifications_list.html', context)


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        user=request.user
    )

    notification.mark_as_read()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'notification_id': notification_id})

    return redirect('accounts:notifications')


@login_required
@require_POST
def mark_all_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(
        user=request.user,
        read_at__isnull=True
    ).update(status='read')

    # Manually set read_at for each
    from django.utils import timezone
    now = timezone.now()
    unread_notifications = Notification.objects.filter(
        user=request.user,
        read_at__isnull=True
    )
    for notification in unread_notifications:
        notification.read_at = now
        notification.save(update_fields=['read_at'])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})

    return redirect('accounts:notifications')


@login_required
def notification_preferences(request):
    """Manage notification preferences"""
    prefs, created = NotificationPreference.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # Update preferences
        prefs.enable_in_app = request.POST.get('enable_in_app') == 'on'
        prefs.enable_sms = request.POST.get('enable_sms') == 'on'
        prefs.enable_whatsapp = request.POST.get('enable_whatsapp') == 'on'
        prefs.enable_email = request.POST.get('enable_email') == 'on'

        prefs.ride_notifications = request.POST.get('ride_notifications') == 'on'
        prefs.food_notifications = request.POST.get('food_notifications') == 'on'
        prefs.shop_notifications = request.POST.get('shop_notifications') == 'on'
        prefs.pharmacy_notifications = request.POST.get('pharmacy_notifications') == 'on'
        prefs.rental_notifications = request.POST.get('rental_notifications') == 'on'
        prefs.subscription_notifications = request.POST.get('subscription_notifications') == 'on'

        prefs.promotional_notifications = request.POST.get('promotional_notifications') == 'on'

        prefs.save()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': 'Preferences updated successfully'})

        return redirect('accounts:notification_preferences')

    context = {
        'preferences': prefs
    }

    return render(request, 'accounts/notification_preferences.html', context)


@login_required
def get_unread_count(request):
    """API endpoint to get unread notification count"""
    count = Notification.objects.filter(
        user=request.user,
        channel='in_app',
        read_at__isnull=True
    ).count()

    return JsonResponse({'unread_count': count})
