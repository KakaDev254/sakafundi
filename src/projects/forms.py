# projects/forms.py
from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from decimal import Decimal

from .models import (
    Project, ProjectUpdate, Dispute, ProjectMilestone, ProjectDocument,
    Order, OrderLineItem, OrderInspiration,
)


# ============================================================
# LEGACY PROJECT FORMS
# ============================================================

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['title', 'description', 'requirements', 'agreed_price']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter project title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describe your project in detail...'
            }),
            'requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'List any specific requirements...'
            }),
            'agreed_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter agreed price (KES)',
                'min': 0,
                'step': '0.01'
            }),
        }
        help_texts = {
            'requirements': 'You can list specific requirements, deliverables, or expectations',
        }

    def clean_agreed_price(self):
        price = self.cleaned_data.get('agreed_price')
        if price and price <= 0:
            raise forms.ValidationError('Price must be greater than 0.')
        return price


class ProjectUpdateForm(forms.ModelForm):
    class Meta:
        model = ProjectUpdate
        fields = ['content', 'attachment', 'type']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
        }


class DisputeForm(forms.ModelForm):
    class Meta:
        model = Dispute
        fields = ['reason', 'title', 'description', 'attachment']
        widgets = {
            'reason': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }


class ProjectMilestoneForm(forms.ModelForm):
    class Meta:
        model = ProjectMilestone
        fields = ['title', 'description', 'due_date', 'is_mandatory', 'attachment']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_mandatory': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }


class ProjectDocumentForm(forms.ModelForm):
    class Meta:
        model = ProjectDocument
        fields = ['title', 'document_type', 'file', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ProjectInvitationForm(forms.Form):
    recipient_email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': "Enter provider's email"
    }))
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )


class ProjectFilterForm(forms.Form):
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(Project.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    role = forms.ChoiceField(
        choices=[
            ('', 'All Roles'),
            ('customer', 'As Customer'),
            ('provider', 'As Provider'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    sort_by = forms.ChoiceField(
        choices=[
            ('-created_at', 'Newest First'),
            ('created_at', 'Oldest First'),
            ('-agreed_price', 'Highest Price'),
            ('agreed_price', 'Lowest Price'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search projects...'})
    )


# ============================================================
# ORDER FORMS — Phase 3A
# ============================================================

class OrderForm(forms.ModelForm):
    """Client submits an order to a fundi."""

    selected_sample_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_selected_sample_id'})
    )

    class Meta:
        model = Order
        fields = [
            'title',
            'description',
            'materials_mode',
            'materials_notes',
            'agreed_price',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Custom oak dining table for 6',
                'maxlength': 200,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': (
                    'Describe what you want done — dimensions, finish, '
                    'style, colours, deadlines...'
                ),
            }),
            'materials_mode': forms.RadioSelect(attrs={
                'class': 'form-check-input',
            }),
            'materials_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': (
                    'If you are providing materials, list them here: '
                    'e.g. 5kg oak wood, varnish, screws...'
                ),
            }),
            'agreed_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 15000',
                'min': 100,
                'step': '100',
                'id': 'id_agreed_price',
            }),
        }
        labels = {
            'title': 'What do you want done?',
            'description': 'Details',
            'materials_mode': 'Materials',
            'materials_notes': 'Materials details',
            'agreed_price': 'Your budget (KSh)',
        }
        help_texts = {
            'agreed_price': 'The labour price you are offering. The fundi can accept or counter.',
        }

    def clean_agreed_price(self):
        price = self.cleaned_data.get('agreed_price')
        if price is not None and price < 100:
            raise ValidationError('Minimum order value is KSh 100.')
        return price

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get('materials_mode')
        notes = cleaned.get('materials_notes')
        if mode == 'client_provides' and not notes:
            self.add_error(
                'materials_notes',
                'Please list the materials you will provide.'
            )
        return cleaned


class OrderInspirationForm(forms.ModelForm):
    """One inspiration image."""

    class Meta:
        model = OrderInspiration
        fields = ['image', 'note']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'note': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional: what about this image do you like?',
                'maxlength': 200,
            }),
        }


class OrderLineItemForm(forms.ModelForm):
    class Meta:
        model = OrderLineItem
        fields = ['title', 'description', 'quantity', 'unit', 'unit_price', 'provided_by']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'kg / piece / metre'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'provided_by': forms.Select(attrs={'class': 'form-select'}),
        }


OrderLineItemFormSet = inlineformset_factory(
    Order,
    OrderLineItem,
    form=OrderLineItemForm,
    extra=0,
    can_delete=True,
    min_num=0,
    validate_min=False,
)


class OrderDeclineForm(forms.Form):
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional: let the client know why you cannot take this order.',
        })
    )


class OrderCancelForm(forms.Form):
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional: let the fundi know why you are cancelling.',
        })
    )