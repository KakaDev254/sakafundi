# chat/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Q, Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.conf import settings
import json
import mimetypes
import os

from .models import Conversation, Message, BlockedUser, ChatUserStatus
from .forms import MessageForm, StartConversationForm
from accounts.models import User
from projects.models import Project
from notifications.models import Notification


@login_required
def chat_list(request):
    """List all conversations for the user"""
    user = request.user
    
    # Get all conversations
    conversations = Conversation.objects.filter(
        participants=user,
        is_active=True
    ).select_related('project').prefetch_related('participants')
    
    # Annotate with latest message and unread count
    for conv in conversations:
        conv.unread_count = conv.get_unread_count(user)
        conv.last_message = conv.get_last_message()
        conv.other_participant = conv.participants.exclude(id=user.id).first()
        conv.is_blocked = BlockedUser.objects.filter(
            blocker=user,
            blocked=conv.other_participant
        ).exists()
        
        # Get online status
        if conv.other_participant:
            try:
                status = ChatUserStatus.objects.get(user=conv.other_participant)
                conv.other_participant.is_online = status.status == 'online'
            except ChatUserStatus.DoesNotExist:
                conv.other_participant.is_online = False
    
    # Sort by latest message
    conversations = sorted(
        conversations, 
        key=lambda x: x.last_message.created_at if x.last_message else x.updated_at, 
        reverse=True
    )
    
    # Pagination
    paginator = Paginator(conversations, 20)
    page = request.GET.get('page')
    
    try:
        conversations = paginator.page(page)
    except PageNotAnInteger:
        conversations = paginator.page(1)
    except EmptyPage:
        conversations = paginator.page(paginator.num_pages)
    
    context = {
        'conversations': conversations,
        'total_unread': sum(conv.unread_count for conv in conversations),
    }
    return render(request, 'chat/list.html', context)


@login_required
def chat_detail(request, conversation_id):
    """View a specific conversation"""
    conversation = get_object_or_404(
        Conversation, 
        id=conversation_id, 
        participants=request.user,
        is_active=True
    )
    
    # Get other participant
    other_participant = conversation.participants.exclude(id=request.user.id).first()
    
    if not other_participant:
        messages.error(request, 'Conversation has no other participant.')
        return redirect('chat:list')
    
    # Check if blocked
    is_blocked = BlockedUser.objects.filter(
        blocker=request.user,
        blocked=other_participant
    ).exists()
    
    is_blocked_by_other = BlockedUser.objects.filter(
        blocker=other_participant,
        blocked=request.user
    ).exists()
    
    if is_blocked_by_other:
        messages.warning(request, 'You cannot message this user as they have blocked you.')
        return redirect('chat:list')
    
    # Mark messages as read
    conversation.mark_all_read(request.user)
    
    # Get messages - limit to last 50 for initial load
    messages_list = conversation.messages.all().order_by('-created_at')[:50]
    messages_list = reversed(messages_list)  # Reverse for chronological order
    
    # Get project info if exists
    project = conversation.project
    
    # Get online status
    try:
        status = ChatUserStatus.objects.get(user=other_participant)
        other_participant.is_online = status.status == 'online'
    except ChatUserStatus.DoesNotExist:
        other_participant.is_online = False
    
    context = {
        'conversation': conversation,
        'messages': messages_list,
        'other_participant': other_participant,
        'project': project,
        'is_blocked': is_blocked,
        'is_blocked_by_other': is_blocked_by_other,
        'message_count': conversation.messages.count(),
    }
    return render(request, 'chat/detail.html', context)


@login_required
@require_POST
def send_message(request, conversation_id):
    """Send a message via POST (fallback)"""
    conversation = get_object_or_404(
        Conversation, 
        id=conversation_id, 
        participants=request.user,
        is_active=True
    )
    
    other_participant = conversation.participants.exclude(id=request.user.id).first()
    if other_participant:
        is_blocked_by_other = BlockedUser.objects.filter(
            blocker=other_participant,
            blocked=request.user
        ).exists()
        
        if is_blocked_by_other:
            return JsonResponse({'error': 'You are blocked by this user'}, status=403)
    
    form = MessageForm(request.POST, request.FILES)
    
    if form.is_valid():
        message = form.save(commit=False)
        message.conversation = conversation
        message.sender = request.user
        message.save()
        
        conversation.save()
        
        # Create notification for other participants
        for participant in conversation.participants.exclude(id=request.user.id):
            Notification.objects.create(
                user=participant,
                type='message',
                title='New Message',
                message=f'{request.user.get_full_name()} sent you a message',
                link=f'/chat/conversation/{conversation.id}/'
            )
        
        return JsonResponse({
            'success': True,
            'message_id': message.id,
            'content': message.content,
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M'),
            'sender': request.user.get_full_name() or request.user.username,
            'sender_id': request.user.id,
        })
    
    return JsonResponse({'error': 'Invalid form data'}, status=400)


@login_required
@require_POST
def mark_read(request, conversation_id):
    """Mark all messages as read"""
    conversation = get_object_or_404(
        Conversation, 
        id=conversation_id, 
        participants=request.user,
        is_active=True
    )
    
    conversation.mark_all_read(request.user)
    
    return JsonResponse({
        'success': True,
        'unread_count': conversation.get_unread_count(request.user)
    })


@login_required
def start_conversation(request):
    """Start a new conversation"""
    if request.method == 'POST':
        form = StartConversationForm(request.POST)
        if form.is_valid():
            recipient_id = form.cleaned_data['recipient_id']
            message_text = form.cleaned_data.get('message', '')
            
            if recipient_id == request.user.id:
                messages.error(request, 'You cannot start a conversation with yourself.')
                return redirect('chat:start')
            
            # Check if blocked
            is_blocked = BlockedUser.objects.filter(
                Q(blocker=request.user, blocked_id=recipient_id) |
                Q(blocker_id=recipient_id, blocked=request.user)
            ).exists()
            
            if is_blocked:
                messages.error(request, 'You cannot start a conversation with this user.')
                return redirect('chat:start')
            
            # Check if conversation exists
            existing_conversations = Conversation.objects.filter(
                participants=request.user,
                is_active=True
            ).filter(participants=recipient_id)
            
            if existing_conversations.exists():
                conversation = existing_conversations.first()
                messages.info(request, 'Conversation already exists.')
                return redirect('chat:detail', conversation_id=conversation.id)
            
            # Create new conversation
            conversation = Conversation.objects.create(is_active=True)
            conversation.participants.add(request.user, recipient_id)
            
            if message_text:
                Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    content=message_text
                )
            
            return redirect('chat:detail', conversation_id=conversation.id)
    else:
        form = StartConversationForm()
    
    recent_users = User.objects.exclude(id=request.user.id).order_by('-last_active')[:10]
    
    context = {
        'form': form,
        'recent_users': recent_users,
    }
    return render(request, 'chat/start.html', context)


@login_required
def start_conversation_with_user(request, user_id):
    """Start conversation with a specific user"""
    recipient = get_object_or_404(User, id=user_id, is_active=True)
    
    if recipient == request.user:
        messages.error(request, 'You cannot start a conversation with yourself.')
        return redirect('chat:list')
    
    is_blocked = BlockedUser.objects.filter(
        Q(blocker=request.user, blocked=recipient) |
        Q(blocker=recipient, blocked=request.user)
    ).exists()
    
    if is_blocked:
        messages.error(request, 'You cannot start a conversation with this user.')
        return redirect('chat:list')
    
    existing_conversations = Conversation.objects.filter(
        participants=request.user,
        is_active=True
    ).filter(participants=recipient)
    
    if existing_conversations.exists():
        conversation = existing_conversations.first()
        return redirect('chat:detail', conversation_id=conversation.id)
    
    conversation = Conversation.objects.create(is_active=True)
    conversation.participants.add(request.user, recipient)
    
    return redirect('chat:detail', conversation_id=conversation.id)


@login_required
def start_from_project(request, project_id):
    """Start conversation from a project"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.user not in [project.customer, project.provider]:
        messages.error(request, 'You are not part of this project.')
        return redirect('projects:detail', project_id=project.id)
    
    other_participant = project.provider if request.user == project.customer else project.customer
    
    conversation, created = Conversation.objects.get_or_create(
        project=project,
        defaults={'is_active': True}
    )
    
    if created:
        conversation.participants.add(project.customer, project.provider)
    
    return redirect('chat:detail', conversation_id=conversation.id)


@login_required
def delete_conversation(request, conversation_id):
    """Delete a conversation (soft delete)"""
    conversation = get_object_or_404(
        Conversation, 
        id=conversation_id, 
        participants=request.user
    )
    
    if request.method == 'POST':
        conversation.is_active = False
        conversation.save()
        messages.success(request, 'Conversation deleted.')
        return redirect('chat:list')
    
    return render(request, 'chat/delete_confirm.html', {'conversation': conversation})


@login_required
def leave_conversation(request, conversation_id):
    """Leave a conversation"""
    conversation = get_object_or_404(
        Conversation, 
        id=conversation_id, 
        participants=request.user
    )
    
    if request.method == 'POST':
        conversation.participants.remove(request.user)
        
        if conversation.participants.count() == 0:
            conversation.is_active = False
            conversation.save()
        
        messages.success(request, 'You have left the conversation.')
        return redirect('chat:list')
    
    return render(request, 'chat/leave_confirm.html', {'conversation': conversation})


@login_required
@require_GET
def get_unread_count(request):
    """Get unread message count for the user"""
    conversations = Conversation.objects.filter(
        participants=request.user,
        is_active=True
    )
    
    total_unread = 0
    for conv in conversations:
        total_unread += conv.get_unread_count(request.user)
    
    return JsonResponse({'unread_count': total_unread})


@login_required
@require_GET
def get_unread_messages(request):
    """Get unread messages for the user"""
    conversations = Conversation.objects.filter(
        participants=request.user,
        is_active=True
    )
    
    unread_messages = []
    for conv in conversations:
        messages = conv.messages.filter(is_read=False).exclude(sender=request.user)[:5]
        for msg in messages:
            unread_messages.append({
                'id': msg.id,
                'conversation_id': conv.id,
                'sender_name': msg.sender.get_full_name() or msg.sender.username,
                'content': msg.content[:100],
                'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M'),
                'conversation_title': conv.project.title if conv.project else 'Direct Message'
            })
    
    return JsonResponse({'unread_messages': unread_messages})


@login_required
def view_attachment(request, message_id):
    """View message attachment"""
    message = get_object_or_404(Message, id=message_id)
    
    if request.user not in message.conversation.participants.all():
        return HttpResponse('Unauthorized', status=401)
    
    if not message.attachment:
        return HttpResponse('No attachment', status=404)
    
    return redirect(message.attachment.url)


@login_required
def download_attachment(request, message_id):
    """Download message attachment"""
    message = get_object_or_404(Message, id=message_id)
    
    if request.user not in message.conversation.participants.all():
        return HttpResponse('Unauthorized', status=401)
    
    if not message.attachment:
        return HttpResponse('No attachment', status=404)
    
    file_path = message.attachment.path
    file_name = os.path.basename(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)
    
    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type=mime_type or 'application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response


@login_required
@require_GET
def search_conversations(request):
    """Search through conversations"""
    query = request.GET.get('q', '')
    
    if not query:
        return JsonResponse({'results': []})
    
    conversations = Conversation.objects.filter(
        participants=request.user,
        is_active=True
    )
    
    messages = Message.objects.filter(
        conversation__in=conversations,
        content__icontains=query
    ).select_related('conversation', 'sender')[:20]
    
    results = []
    for msg in messages:
        results.append({
            'id': msg.id,
            'content': msg.content[:200],
            'conversation_id': msg.conversation.id,
            'sender_name': msg.sender.get_full_name() or msg.sender.username,
            'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M'),
        })
    
    return JsonResponse({'results': results})


@login_required
@require_GET
def search_users(request):
    """Search for users to chat with"""
    query = request.GET.get('q', '')
    
    if not query:
        return JsonResponse({'users': []})
    
    users = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query)
    ).exclude(id=request.user.id)[:10]
    
    results = []
    for user in users:
        results.append({
            'id': user.id,
            'name': user.get_full_name() or user.username,
            'email': user.email,
            'profile_image': user.profile_image.url if user.profile_image else None,
            'is_provider': user.is_provider(),
        })
    
    return JsonResponse({'users': results})


@login_required
@require_POST
def block_user(request, user_id):
    """Block a user"""
    user_to_block = get_object_or_404(User, id=user_id)
    
    if user_to_block == request.user:
        return JsonResponse({'error': 'Cannot block yourself'}, status=400)
    
    blocked, created = BlockedUser.objects.get_or_create(
        blocker=request.user,
        blocked=user_to_block
    )
    
    if created:
        conversations = Conversation.objects.filter(
            participants=request.user,
            is_active=True
        ).filter(participants=user_to_block)
        
        for conv in conversations:
            conv.participants.remove(request.user)
        
        return JsonResponse({'success': True, 'message': 'User blocked successfully'})
    
    return JsonResponse({'success': False, 'message': 'User already blocked'})


@login_required
@require_POST
def unblock_user(request, user_id):
    """Unblock a user"""
    user_to_unblock = get_object_or_404(User, id=user_id)
    
    blocked = BlockedUser.objects.filter(
        blocker=request.user,
        blocked=user_to_unblock
    ).first()
    
    if blocked:
        blocked.delete()
        return JsonResponse({'success': True, 'message': 'User unblocked successfully'})
    
    return JsonResponse({'success': False, 'message': 'User not blocked'})