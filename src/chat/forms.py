# chat/forms.py
from django import forms
from .models import Message, Conversation

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content', 'attachment']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Type your message...',
                'style': 'resize: none;'
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,.pdf,.doc,.docx,.txt,.zip'
            }),
        }
    
    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        if attachment:
            # Max file size: 10MB
            if attachment.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File size must be less than 10MB.')
            
            # Allowed file types
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 
                           'application/pdf', 'application/msword', 
                           'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                           'text/plain', 'application/zip']
            
            if attachment.content_type not in allowed_types:
                raise forms.ValidationError('File type not allowed.')
        
        return attachment


class StartConversationForm(forms.Form):
    recipient_id = forms.IntegerField(
        widget=forms.HiddenInput()
    )
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional initial message...'
        })
    )
    
    def clean_recipient_id(self):
        recipient_id = self.cleaned_data.get('recipient_id')
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            User.objects.get(id=recipient_id, is_active=True)
        except User.DoesNotExist:
            raise forms.ValidationError('User does not exist.')
        
        return recipient_id


class ChatSearchForm(forms.Form):
    query = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search messages...'
        })
    )