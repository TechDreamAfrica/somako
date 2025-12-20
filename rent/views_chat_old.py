"""
Chat views for rental messaging between renters and landlords
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Equipment, RentalMessage
from .forms import RentalMessageForm

try:
    from accounts.notification_service import NotificationService
    HAS_NOTIFICATION_SERVICE = True
except ImportError:
    HAS_NOTIFICATION_SERVICE = False


@login_required
def send_message(request):
    """Send a message to property/equipment owner"""
    if request.method == 'POST':
        message_type = request.POST.get('message_type')
        item_id = request.POST.get('item_id')
        message_text = request.POST.get('message')

        if not all([message_type, item_id, message_text]):
            messages.error(request, 'Missing required fields.')
            return redirect(request.META.get('HTTP_REFERER', 'rent:property_list'))

        try:
            # Get the item
            if message_type == 'property':
                item = get_object_or_404(Property, pk=item_id)
                owner = item.owner
            else:  # equipment
                item = get_object_or_404(Equipment, pk=item_id)
                owner = item.owner

            # Determine the receiver
            # If current user is the owner, find the other party from existing messages
            if request.user == owner:
                # Owner is replying - find the renter from previous messages
                existing_messages = RentalMessage.objects.filter(
                    message_type=message_type,
                    **{message_type: item}
                ).exclude(sender=request.user).order_by('-created_at')

                if existing_messages.exists():
                    # Reply to the most recent sender
                    receiver = existing_messages.first().sender
                else:
                    messages.error(request, 'No conversation found to reply to.')
                    return redirect(request.META.get('HTTP_REFERER', 'rent:property_list'))
            else:
                # Renter is sending message to owner
                receiver = owner

            # Create the message
            rental_message = RentalMessage.objects.create(
                message_type=message_type,
                sender=request.user,
                receiver=receiver,
                property=item if message_type == 'property' else None,
                equipment=item if message_type == 'equipment' else None,
                message=message_text
            )

            # Send SMS notification to landlord if available
            if HAS_NOTIFICATION_SERVICE:
                item_name = item.title if message_type == 'property' else item.name
                notification_service = NotificationService()

                # Create the message with a link
                chat_url = request.build_absolute_uri(
                    f'/rent/chat/?{message_type}={item_id}'
                )

                notification_message = (
                    f"New message from {request.user.username} about your {message_type} '{item_name}'. "
                    f"Click to view and reply: {chat_url}"
                )

                try:
                    notification_service.send_notification(
                        user=receiver,
                        notification_type='message_received',
                        title='New Message',
                        message=notification_message,
                        channels=['in_app', 'sms'],
                        reference_id=str(rental_message.id),
                        reference_type='rental_message',
                        data={
                            'message_type': message_type,
                            'item_id': item_id,
                            'sender_id': request.user.id,
                            'chat_url': chat_url
                        }
                    )
                except Exception as e:
                    # Log but don't fail if notification fails
                    print(f"Failed to send notification: {e}")

            messages.success(request, 'Message sent successfully!')

            # Redirect to chat thread
            return redirect(f'/rent/chat/?{message_type}={item_id}')

        except Exception as e:
            messages.error(request, f'Error sending message: {str(e)}')
            return redirect(request.META.get('HTTP_REFERER', 'rent:property_list'))

    return redirect('rent:property_list')


@login_required
def chat_thread(request):
    """View chat thread for a property or equipment"""
    message_type = request.GET.get('property') and 'property' or request.GET.get('equipment') and 'equipment'
    item_id = request.GET.get('property') or request.GET.get('equipment')

    if not message_type or not item_id:
        messages.error(request, 'Invalid chat thread.')
        return redirect('rent:property_list')

    try:
        # Get the item
        if message_type == 'property':
            item = get_object_or_404(Property, pk=item_id)
            owner = item.owner
        else:
            item = get_object_or_404(Equipment, pk=item_id)
            owner = item.owner

        # Get all messages for this item
        chat_messages = RentalMessage.objects.filter(
            message_type=message_type,
            **{message_type: item}
        ).select_related('sender', 'receiver').order_by('created_at')

        # Mark messages as read if user is receiver
        unread_messages = chat_messages.filter(
            receiver=request.user,
            is_read=False
        )
        for msg in unread_messages:
            msg.mark_as_read()

        # Determine who the other party is
        other_party = owner if request.user != owner else None
        if not other_party and chat_messages.exists():
            # If user is owner, find the other party from messages
            for msg in chat_messages:
                if msg.sender != request.user:
                    other_party = msg.sender
                    break
                elif msg.receiver != request.user:
                    other_party = msg.receiver
                    break

        # Get display name for the item
        item_name = item.title if message_type == 'property' else item.name

        context = {
            'item': item,
            'item_name': item_name,
            'message_type': message_type,
            'chat_messages': chat_messages,
            'other_party': other_party,
            'is_owner': request.user == owner,
            'form': RentalMessageForm(),
        }

        return render(request, 'rent/chat_thread.html', context)

    except Exception as e:
        messages.error(request, f'Error loading chat: {str(e)}')
        return redirect('rent:property_list')


@login_required
def my_messages(request):
    """View all messages (inbox)"""
    # Get all conversations (unique property/equipment combinations)
    sent_messages = RentalMessage.objects.filter(sender=request.user)
    received_messages = RentalMessage.objects.filter(receiver=request.user)

    # Combine and get unique conversations
    all_messages = (sent_messages | received_messages).select_related(
        'property', 'equipment', 'sender', 'receiver'
    ).order_by('-created_at')

    # Group by property/equipment
    conversations = {}
    for msg in all_messages:
        if msg.message_type == 'property':
            key = f'property_{msg.property.id}'
            if key not in conversations:
                conversations[key] = {
                    'item': msg.property,
                    'type': 'property',
                    'last_message': msg,
                    'unread_count': received_messages.filter(
                        property=msg.property,
                        is_read=False
                    ).count()
                }
        else:
            key = f'equipment_{msg.equipment.id}'
            if key not in conversations:
                conversations[key] = {
                    'item': msg.equipment,
                    'type': 'equipment',
                    'last_message': msg,
                    'unread_count': received_messages.filter(
                        equipment=msg.equipment,
                        is_read=False
                    ).count()
                }

    context = {
        'conversations': conversations.values(),
    }

    return render(request, 'rent/my_messages.html', context)
