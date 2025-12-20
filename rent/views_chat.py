"""
Views for chat/messaging functionality between renters and equipment owners
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import models
from .models import Equipment, RentalMessage


@login_required
def send_message(request):
    """Send a message to equipment owner"""
    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        item_id = request.POST.get('equipment')
        
        if not message_text:
            messages.error(request, 'Message cannot be empty.')
            return redirect(request.META.get('HTTP_REFERER', 'rent:equipment_list'))
        
        if not item_id:
            messages.error(request, 'Item not specified.')
            return redirect(request.META.get('HTTP_REFERER', 'rent:equipment_list'))
        
        try:
            item = get_object_or_404(Equipment, pk=item_id)
            
            # Check if user is trying to message themselves
            if item.owner == request.user:
                messages.error(request, 'You cannot send a message to yourself.')
                return redirect(request.META.get('HTTP_REFERER', 'rent:equipment_list'))
            
            # Create the message
            rental_message = RentalMessage.objects.create(
                sender=request.user,
                receiver=item.owner,
                equipment=item,
                message=message_text
            )
            
            # Success message
            item_name = item.name
            messages.success(request, f'Message sent to {item.owner.username} about "{item_name}"')
            
            # Redirect back to the item detail page or wherever they came from
            return redirect(request.META.get('HTTP_REFERER', 'rent:equipment_detail', kwargs={'pk': item_id}))
            
        except Exception as e:
            messages.error(request, f'Error sending message: {str(e)}')
            return redirect(request.META.get('HTTP_REFERER', 'rent:equipment_list'))
    
    # If not POST, redirect to equipment list
    messages.error(request, 'Invalid request method.')
    return redirect('rent:equipment_list')


@login_required
def chat_thread(request):
    """View chat thread for equipment"""
    equipment_id = request.GET.get('equipment')
    
    if not equipment_id:
        messages.error(request, 'Equipment not specified.')
        return redirect('rent:equipment_list')
    
    try:
        item = get_object_or_404(Equipment, pk=equipment_id)
        
        # Get all messages for this equipment between current user and owner
        if request.user == item.owner:
            # Owner sees all messages for their equipment
            chat_messages = RentalMessage.objects.filter(
                equipment=item
            ).order_by('created_at')
        else:
            # Renter sees only messages between them and owner
            chat_messages = RentalMessage.objects.filter(
                equipment=item,
                sender__in=[request.user, item.owner],
                receiver__in=[request.user, item.owner]
            ).order_by('created_at')
        
        # Mark messages as read if user is the receiver
        unread_messages = chat_messages.filter(receiver=request.user, is_read=False)
        for message in unread_messages:
            message.mark_as_read()
        
        item_name = item.name
        
        context = {
            'item': item,
            'item_name': item_name,
            'chat_messages': chat_messages,
            'other_user': item.owner if request.user != item.owner else None,
        }
        
        return render(request, 'rent/chat_thread.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading chat: {str(e)}')
        return redirect('rent:equipment_list')


@login_required
def my_messages(request):
    """View all messages for the current user"""
    
    # Get all conversations (unique equipment combinations)
    conversations = RentalMessage.objects.filter(
        models.Q(sender=request.user) | models.Q(receiver=request.user)
    ).values(
        'equipment', 'sender', 'receiver'
    ).distinct()
    
    # Build conversation list with latest message details
    conversation_list = []
    
    for conv in conversations:
        equipment_id = conv['equipment']
        sender_id = conv['sender']
        receiver_id = conv['receiver']
        
        # Get the equipment
        try:
            equipment = Equipment.objects.get(pk=equipment_id)
        except Equipment.DoesNotExist:
            continue
        
        # Get latest message in this conversation
        latest_message = RentalMessage.objects.filter(
            equipment_id=equipment_id,
            sender_id__in=[sender_id, receiver_id],
            receiver_id__in=[sender_id, receiver_id]
        ).order_by('-created_at').first()
        
        if latest_message:
            # Determine the other participant
            other_user = latest_message.sender if latest_message.sender != request.user else latest_message.receiver
            
            # Count unread messages
            unread_count = RentalMessage.objects.filter(
                equipment_id=equipment_id,
                receiver=request.user,
                is_read=False
            ).count()
            
            conversation_list.append({
                'equipment': equipment,
                'other_user': other_user,
                'latest_message': latest_message,
                'unread_count': unread_count,
            })
    
    # Sort by latest message timestamp
    conversation_list.sort(key=lambda x: x['latest_message'].created_at, reverse=True)
    
    context = {
        'conversations': conversation_list,
    }
    
    return render(request, 'rent/my_messages.html', context)