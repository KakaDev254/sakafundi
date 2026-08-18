# projects/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from cloudinary.models import CloudinaryField

User = get_user_model()

class Project(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('negotiating', 'Negotiating'),
        ('agreed', 'Price Agreed'),
        ('deposit_pending', 'Deposit Pending'),
        ('deposit_paid', 'Deposit Paid'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Work Submitted'),
        ('reviewing', 'Under Review'),
        ('completed', 'Completed'),
        ('final_paid', 'Final Payment Made'),
        ('disputed', 'Disputed'),
        ('cancelled', 'Cancelled'),
    )
    
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects_as_customer')
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects_as_provider')
    service = models.ForeignKey('services.Service', on_delete=models.SET_NULL, null=True)
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    requirements = models.JSONField(null=True, blank=True)
    
    # Pricing
    agreed_price = models.DecimalField(max_digits=12, decimal_places=2)
    deposit_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=30)
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2)
    final_amount = models.DecimalField(max_digits=12, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    provider_payout = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Payment tracking
    deposit_paid = models.BooleanField(default=False)
    deposit_payment_id = models.CharField(max_length=255, null=True, blank=True)
    deposit_paid_at = models.DateTimeField(null=True, blank=True)
    
    final_paid = models.BooleanField(default=False)
    final_payment_id = models.CharField(max_length=255, null=True, blank=True)
    final_paid_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    agreed_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery
    delivery_notes = models.TextField(null=True, blank=True)
    delivery_files = models.JSONField(null=True, blank=True)
    
    # Dispute
    dispute_reason = models.TextField(null=True, blank=True)
    dispute_resolved = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.customer.username}"
    
    def calculate_deposit(self):
        """Calculate deposit amount"""
        return (self.agreed_price * self.deposit_percentage) / 100
    
    def calculate_platform_fee(self):
        """Calculate platform fee (10%)"""
        from django.conf import settings
        return self.agreed_price * (settings.PLATFORM_FEE_PERCENTAGE / 100)
    
    def calculate_provider_payout(self):
        """Calculate what provider receives"""
        return self.agreed_price - self.calculate_platform_fee()
    
    def get_status_display(self):
        """Get human-readable status"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    def is_active(self):
        """Check if project is active"""
        return self.status not in ['completed', 'cancelled', 'disputed']
    
    def can_edit(self, user):
        """Check if user can edit project"""
        return user == self.customer and self.status in ['draft', 'negotiating']
    
    def can_accept(self, user):
        """Check if provider can accept project"""
        return user == self.provider and self.status == 'negotiating'
    
    def can_start(self, user):
        """Check if provider can start project"""
        return user == self.provider and self.status == 'deposit_paid'
    
    def can_submit(self, user):
        """Check if provider can submit work"""
        return user == self.provider and self.status == 'in_progress'
    
    def can_complete(self, user):
        """Check if customer can complete project"""
        return user == self.customer and self.status == 'submitted'
    
    def can_pay_deposit(self, user):
        """Check if customer can pay deposit"""
        return user == self.customer and self.status == 'agreed' and not self.deposit_paid
    
    def can_pay_final(self, user):
        """Check if customer can pay final"""
        return user == self.customer and self.status == 'submitted' and not self.final_paid
    
    def can_dispute(self, user):
        """Check if user can dispute project"""
        return user in [self.customer, self.provider] and self.status not in ['completed', 'cancelled', 'disputed']


class ProjectUpdate(models.Model):
    """Updates and progress reports on a project"""
    UPDATE_TYPES = (
        ('general', 'General Update'),
        ('submission', 'Work Submission'),
        ('revision', 'Revision Request'),
        ('payment', 'Payment Update'),
        ('status_change', 'Status Change'),
        ('dispute', 'Dispute Update'),
    )
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='updates')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=UPDATE_TYPES, default='general')
    content = models.TextField()
    
    # Using CloudinaryField for attachments
    attachment = CloudinaryField(
        'file',
        folder='project_updates',
        blank=True,
        null=True
    )
    attachment_name = models.CharField(max_length=255, null=True, blank=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Update on {self.project.title} by {self.user.username} at {self.created_at}"
    
    def get_type_display(self):
        """Get human-readable type"""
        return dict(self.UPDATE_TYPES).get(self.type, self.type)


class Dispute(models.Model):
    """Dispute resolution for projects"""
    DISPUTE_STATUS = (
        ('open', 'Open'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('escalated', 'Escalated to Admin'),
    )
    
    DISPUTE_REASONS = (
        ('quality', 'Quality Issues'),
        ('delivery', 'Late Delivery'),
        ('payment', 'Payment Issues'),
        ('communication', 'Communication Breakdown'),
        ('scope', 'Scope Creep'),
        ('other', 'Other'),
    )
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='disputes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disputes_raised')
    
    reason = models.CharField(max_length=20, choices=DISPUTE_REASONS, default='other')
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Using CloudinaryField for attachments
    attachment = CloudinaryField(
        'file',
        folder='disputes',
        blank=True,
        null=True
    )
    attachment_name = models.CharField(max_length=255, null=True, blank=True)
    
    # Admin/Resolution
    status = models.CharField(max_length=20, choices=DISPUTE_STATUS, default='open')
    resolution = models.TextField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='disputes_resolved'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Admin notes
    admin_notes = models.TextField(blank=True, null=True)
    is_escalated = models.BooleanField(default=False)
    escalated_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Disputes'
    
    def __str__(self):
        return f"Dispute: {self.title} - {self.project.title}"
    
    def get_reason_display(self):
        """Get human-readable reason"""
        return dict(self.DISPUTE_REASONS).get(self.reason, self.reason)
    
    def get_status_display(self):
        """Get human-readable status"""
        return dict(self.DISPUTE_STATUS).get(self.status, self.status)
    
    def resolve(self, user, resolution):
        """Resolve the dispute"""
        self.status = 'resolved'
        self.resolution = resolution
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.save()
        
        # Update project status
        self.project.dispute_resolved = True
        self.project.status = 'in_progress'  # Return to in progress
        self.project.save()
    
    def escalate(self):
        """Escalate dispute to admin"""
        self.status = 'escalated'
        self.is_escalated = True
        self.escalated_at = timezone.now()
        self.save()


class ProjectMilestone(models.Model):
    """Milestones for a project"""
    MILESTONE_STATUS = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('delayed', 'Delayed'),
        ('cancelled', 'Cancelled'),
    )
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Timeline
    due_date = models.DateField()
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=MILESTONE_STATUS, default='pending')
    is_mandatory = models.BooleanField(default=True)
    
    # Attachments - Using CloudinaryField
    attachment = CloudinaryField(
        'file',
        folder='milestones',
        blank=True,
        null=True
    )
    
    # Ordering
    order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'due_date']
    
    def __str__(self):
        return f"{self.project.title} - {self.title}"
    
    def is_overdue(self):
        """Check if milestone is overdue"""
        return self.status != 'completed' and timezone.now().date() > self.due_date
    
    def complete(self):
        """Mark milestone as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()


class ProjectDocument(models.Model):
    """Documents uploaded for a project"""
    DOCUMENT_TYPES = (
        ('contract', 'Contract'),
        ('agreement', 'Agreement'),
        ('invoice', 'Invoice'),
        ('receipt', 'Receipt'),
        ('design', 'Design File'),
        ('code', 'Code File'),
        ('report', 'Report'),
        ('other', 'Other'),
    )
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='documents')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='other')
    
    # Using CloudinaryField for files
    file = CloudinaryField(
        'file',
        folder='project_documents',
        blank=True,
        null=True
    )
    description = models.TextField(blank=True, null=True)
    
    # Versioning
    version = models.CharField(max_length=20, default='1.0')
    is_latest = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.project.title} - {self.title}"
    
    def get_document_type_display(self):
        """Get human-readable document type"""
        return dict(self.DOCUMENT_TYPES).get(self.document_type, self.document_type)


class ProjectActivity(models.Model):
    """Activity log for projects"""
    ACTIVITY_TYPES = (
        ('created', 'Project Created'),
        ('updated', 'Project Updated'),
        ('status_change', 'Status Changed'),
        ('payment', 'Payment Made'),
        ('message', 'Message Sent'),
        ('file_upload', 'File Uploaded'),
        ('milestone_completed', 'Milestone Completed'),
        ('dispute_raised', 'Dispute Raised'),
        ('dispute_resolved', 'Dispute Resolved'),
    )
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField()
    metadata = models.JSONField(null=True, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Project Activities'
    
    def __str__(self):
        return f"{self.project.title} - {self.activity_type} by {self.user.username}"
    
    def get_activity_type_display(self):
        """Get human-readable activity type"""
        return dict(self.ACTIVITY_TYPES).get(self.activity_type, self.activity_type)


class ProjectInvitation(models.Model):
    """Invitations for providers to join projects"""
    INVITATION_STATUS = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    )
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='invitations')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invitations')
    
    message = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=INVITATION_STATUS, default='pending')
    
    # Expiry
    expires_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Invitation from {self.sender.username} to {self.recipient.username} for {self.project.title}"
    
    def is_expired(self):
        """Check if invitation has expired"""
        return timezone.now() > self.expires_at
    
    def accept(self):
        """Accept the invitation"""
        self.status = 'accepted'
        self.responded_at = timezone.now()
        self.save()
        
        # Add recipient as provider to project
        self.project.provider = self.recipient
        self.project.save()
    
    def decline(self):
        """Decline the invitation"""
        self.status = 'declined'
        self.responded_at = timezone.now()
        self.save()