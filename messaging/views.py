"""
Generic messaging views for cross-app communication
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from .models import Message, Conversation


@login_required
def send_message(request):
    """Send a message to another user about a specific object"""
    if request.method == 'POST':
        app_type = request.POST.get('app_type')
        content_type_id = request.POST.get('content_type_id')
        object_id = request.POST.get('object_id')
        receiver_id = request.POST.get('receiver_id')
        message_text = request.POST.get('message')
        subject = request.POST.get('subject', '')

        if not all([app_type, content_type_id, object_id, receiver_id, message_text]):
            django_messages.error(request, 'Missing required fields.')
            return redirect(request.META.get('HTTP_REFERER', '/'))

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()

            receiver = get_object_or_404(User, id=receiver_id)
            content_type = get_object_or_404(ContentType, id=content_type_id)

            # Prevent sending messages to yourself
            if receiver == request.user:
                django_messages.error(request, 'You cannot send messages to yourself.')
                return redirect(request.META.get('HTTP_REFERER', '/'))

            # Create the message
            message = Message.objects.create(
                app_type=app_type,
                sender=request.user,
                receiver=receiver,
                content_type=content_type,
                object_id=object_id,
                subject=subject,
                message=message_text
            )

            # Create or update conversation
            users = sorted([request.user.id, receiver.id])
            conversation, created = Conversation.objects.get_or_create(
                user1_id=users[0],
                user2_id=users[1],
                content_type=content_type,
                object_id=object_id,
                defaults={'app_type': app_type}
            )

            # Send notification if available
            try:
                from accounts.notification_service import send_notification

                # Get the related object name
                related_object = content_type.get_object_for_this_type(pk=object_id)
                object_name = message.get_related_object_name()

                notification_message = (
                    f"New message from {request.user.get_full_name() or request.user.username} "
                    f"about {object_name}: {message_text[:100]}"
                )

                send_notification(
                    user=receiver,
                    notification_type='message_received',
                    title='New Message',
                    message=notification_message,
                    channels=['in_app', 'sms'],
                    reference_id=str(message.id),
                    reference_type='message',
                    data={
                        'message_id': message.id,
                        'sender_id': request.user.id,
                        'app_type': app_type,
                    }
                )
            except Exception as e:
                # Log but don't fail if notification fails
                print(f"Failed to send notification: {e}")

            django_messages.success(request, 'Message sent successfully!')

            # Redirect to message thread or back
            next_url = request.POST.get('next') or request.META.get('HTTP_REFERER', '/')
            return redirect(next_url)

        except Exception as e:
            django_messages.error(request, f'Error sending message: {str(e)}')
            return redirect(request.META.get('HTTP_REFERER', '/'))

    return redirect('/')


@login_required
def message_thread(request):
    """View a message thread for a specific object"""
    content_type_id = request.GET.get('content_type_id')
    object_id = request.GET.get('object_id')
    other_user_id = request.GET.get('user_id')

    if not all([content_type_id, object_id]):
        django_messages.error(request, 'Invalid message thread.')
        return redirect('messaging:inbox')

    try:
        content_type = get_object_or_404(ContentType, id=content_type_id)
        related_object = content_type.get_object_for_this_type(pk=object_id)

        # Get all messages for this object involving the current user
        thread_messages = Message.objects.filter(
            content_type=content_type,
            object_id=object_id
        ).filter(
            Q(sender=request.user) | Q(receiver=request.user)
        )

        # If other_user_id is specified, filter to that conversation
        if other_user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            other_user = get_object_or_404(User, id=other_user_id)
            thread_messages = thread_messages.filter(
                Q(sender=other_user) | Q(receiver=other_user)
            )
        else:
            # Find the other user from messages
            other_user = None
            for msg in thread_messages:
                if msg.sender != request.user:
                    other_user = msg.sender
                    break
                elif msg.receiver != request.user:
                    other_user = msg.receiver
                    break

        thread_messages = thread_messages.select_related('sender', 'receiver').order_by('created_at')

        # Mark unread messages as read
        unread_messages = thread_messages.filter(receiver=request.user, is_read=False)
        for msg in unread_messages:
            msg.mark_as_read()

        # Handle new message submission
        if request.method == 'POST' and other_user:
            message_text = request.POST.get('message')
            if message_text:
                Message.objects.create(
                    app_type=thread_messages.first().app_type if thread_messages.exists() else 'food',
                    sender=request.user,
                    receiver=other_user,
                    content_type=content_type,
                    object_id=object_id,
                    message=message_text
                )
                django_messages.success(request, 'Message sent!')
                return redirect(f'{request.path}?content_type_id={content_type_id}&object_id={object_id}&user_id={other_user.id}')

        context = {
            'thread_messages': thread_messages,
            'related_object': related_object,
            'other_user': other_user,
            'content_type_id': content_type_id,
            'object_id': object_id,
        }

        return render(request, 'messaging/thread.html', context)

    except Exception as e:
        django_messages.error(request, f'Error loading thread: {str(e)}')
        return redirect('messaging:inbox')


@login_required
def inbox(request):
    """View all message conversations"""
    # Get all messages involving the current user
    user_messages = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).select_related('sender', 'receiver', 'content_type').order_by('-created_at')

    # Group by conversation (content_type + object_id + other_user)
    conversations = {}
    for msg in user_messages:
        # Determine the other user
        other_user = msg.receiver if msg.sender == request.user else msg.sender

        # Create a unique key for this conversation
        key = f'{msg.content_type.id}_{msg.object_id}_{other_user.id}'

        if key not in conversations:
            # Get unread count for this conversation
            unread_count = Message.objects.filter(
                content_type=msg.content_type,
                object_id=msg.object_id,
                receiver=request.user,
                is_read=False
            ).filter(
                Q(sender=other_user)
            ).count()

            conversations[key] = {
                'last_message': msg,
                'other_user': other_user,
                'content_type_id': msg.content_type.id,
                'object_id': msg.object_id,
                'related_object': msg.content_object,
                'unread_count': unread_count,
                'app_type': msg.app_type,
            }

    # Filter by app type if requested
    app_filter = request.GET.get('app')
    if app_filter:
        conversations = {k: v for k, v in conversations.items() if v['app_type'] == app_filter}

    context = {
        'conversations': conversations.values(),
        'app_filter': app_filter,
    }

    return render(request, 'messaging/inbox.html', context)
