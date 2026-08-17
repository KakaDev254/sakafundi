# projects/forms.py
from django import forms
from .models import Project, ProjectUpdate, Dispute, ProjectMilestone, ProjectDocument

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
        if price <= 0:
            raise forms.ValidationError('Price must be greater than 0.')
        return price


class ProjectUpdateForm(forms.ModelForm):
    class Meta:
        model = ProjectUpdate
        fields = ['content', 'attachment', 'type']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your update...'
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'type': forms.Select(attrs={
                'class': 'form-select'
            }),
        }


class DisputeForm(forms.ModelForm):
    class Meta:
        model = Dispute
        fields = ['reason', 'title', 'description', 'attachment']
        widgets = {
            'reason': forms.Select(attrs={
                'class': 'form-select'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dispute title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describe the issue in detail...'
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }


class ProjectMilestoneForm(forms.ModelForm):
    class Meta:
        model = ProjectMilestone
        fields = ['title', 'description', 'due_date', 'is_mandatory', 'attachment']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Milestone title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe this milestone...'
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'is_mandatory': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }


class ProjectDocumentForm(forms.ModelForm):
    class Meta:
        model = ProjectDocument
        fields = ['title', 'document_type', 'file', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Document title'
            }),
            'document_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Document description...'
            }),
        }


class ProjectInvitationForm(forms.Form):
    """Form for inviting providers to a project"""
    recipient_email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter provider\'s email'
    }))
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional personal message...'
        })
    )


class ProjectFilterForm(forms.Form):
    """Form for filtering projects"""
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(Project.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    role = forms.ChoiceField(
        choices=[
            ('', 'All Roles'),
            ('customer', 'As Customer'),
            ('provider', 'As Provider')
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
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search projects...'
        })
    )