# projects/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from cloudinary.models import CloudinaryField

User = get_user_model()


# ============================================================
# LEGACY PROJECT MODEL (kept for existing data)
# ============================================================

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

    agreed_price = models.DecimalField(max_digits=12, decimal_places=2)
    deposit_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=30)
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2)
    final_amount = models.DecimalField(max_digits=12, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    provider_payout = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    deposit_paid = models.BooleanField(default=False)
    deposit_payment_id = models.CharField(max_length=255, null=True, blank=True)
    deposit_paid_at = models.DateTimeField(null=True, blank=True)

    final_paid = models.BooleanField(default=False)
    final_payment_id = models.CharField(max_length=255, null=True, blank=True)
    final_paid_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    agreed_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    delivery_notes = models.TextField(null=True, blank=True)
    delivery_files = models.JSONField(null=True, blank=True)

    dispute_reason = models.TextField(null=True, blank=True)
    dispute_resolved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.customer.username}"

    def calculate_deposit(self):
        return (self.agreed_price * self.deposit_percentage) / 100

    def calculate_platform_fee(self):
        from django.conf import settings
        return self.agreed_price * (settings.PLATFORM_FEE_PERCENTAGE / 100)

    def calculate_provider_payout(self):
        return self.agreed_price - self.calculate_platform_fee()

    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def is_active(self):
        return self.status not in ['completed', 'cancelled', 'disputed']

    def can_edit(self, user):
        return user == self.customer and self.status in ['draft', 'negotiating']

    def can_accept(self, user):
        return user == self.provider and self.status == 'negotiating'

    def can_start(self, user):
        return user == self.provider and self.status == 'deposit_paid'

    def can_submit(self, user):
        return user == self.provider and self.status == 'in_progress'

    def can_complete(self, user):
        return user == self.customer and self.status == 'submitted'

    def can_pay_deposit(self, user):
        return user == self.customer and self.status == 'agreed' and not self.deposit_paid

    def can_pay_final(self, user):
        return user == self.customer and self.status == 'submitted' and not self.final_paid

    def can_dispute(self, user):
        return user in [self.customer, self.provider] and self.status not in ['completed', 'cancelled', 'disputed']


class ProjectUpdate(models.Model):
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

    attachment = CloudinaryField('file', folder='project_updates', blank=True, null=True)
    attachment_name = models.CharField(max_length=255, null=True, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Update on {self.project.title} by {self.user.username}"

    def get_type_display(self):
        return dict(self.UPDATE_TYPES).get(self.type, self.type)


class Dispute(models.Model):
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

    attachment = CloudinaryField('file', folder='disputes', blank=True, null=True)
    attachment_name = models.CharField(max_length=255, null=True, blank=True)

    status = models.CharField(max_length=20, choices=DISPUTE_STATUS, default='open')
    resolution = models.TextField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='disputes_resolved'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

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
        return dict(self.DISPUTE_REASONS).get(self.reason, self.reason)

    def get_status_display(self):
        return dict(self.DISPUTE_STATUS).get(self.status, self.status)

    def resolve(self, user, resolution):
        self.status = 'resolved'
        self.resolution = resolution
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.save()
        self.project.dispute_resolved = True
        self.project.status = 'in_progress'
        self.project.save()

    def escalate(self):
        self.status = 'escalated'
        self.is_escalated = True
        self.escalated_at = timezone.now()
        self.save()


class ProjectMilestone(models.Model):
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

    due_date = models.DateField()
    completed_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=MILESTONE_STATUS, default='pending')
    is_mandatory = models.BooleanField(default=True)

    attachment = CloudinaryField('file', folder='milestones', blank=True, null=True)
    order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'due_date']

    def __str__(self):
        return f"{self.project.title} - {self.title}"

    def is_overdue(self):
        return self.status != 'completed' and timezone.now().date() > self.due_date

    def complete(self):
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()


class ProjectDocument(models.Model):
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

    file = CloudinaryField('file', folder='project_documents', blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    version = models.CharField(max_length=20, default='1.0')
    is_latest = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project.title} - {self.title}"

    def get_document_type_display(self):
        return dict(self.DOCUMENT_TYPES).get(self.document_type, self.document_type)


class ProjectActivity(models.Model):
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
        return f"{self.project.title} - {self.activity_type}"

    def get_activity_type_display(self):
        return dict(self.ACTIVITY_TYPES).get(self.activity_type, self.activity_type)


class ProjectInvitation(models.Model):
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

    expires_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invitation {self.sender.username} → {self.recipient.username}"

    def is_expired(self):
        return timezone.now() > self.expires_at

    def accept(self):
        self.status = 'accepted'
        self.responded_at = timezone.now()
        self.save()
        self.project.provider = self.recipient
        self.project.save()

    def decline(self):
        self.status = 'declined'
        self.responded_at = timezone.now()
        self.save()


# ============================================================
# ORDER MODEL — Phase 3A
# ============================================================
# The Order is the primary marketplace transaction.
# Project remains for legacy data; new transactions use Order.
# ============================================================


class Order(models.Model):
    """
    Marketplace order. Client selects a fundi's sample, agrees on terms,
    gets a quotation, and pays a deposit into escrow. Balance releases
    on approval.
    """

    STATUS_CHOICES = (
        ('pending_acceptance', 'Pending Fundi Acceptance'),
        ('accepted', 'Accepted — Awaiting Deposit'),
        ('deposit_paid', 'Deposit Paid — Ready to Start'),
        ('in_progress', 'In Progress'),
        ('milestone_ready', 'View / Fit Available'),
        ('submitted', 'Work Submitted — Awaiting Approval'),
        ('completed', 'Completed'),
        ('declined', 'Declined by Fundi'),
        ('cancelled', 'Cancelled'),
        ('disputed', 'Disputed'),
    )

    MATERIALS_MODE = (
        ('fundi_provides', 'Fundi provides materials'),
        ('client_provides', 'Client provides materials'),
        ('no_materials', 'No materials required'),
    )

    PAYMENT_PLAN = (
        ('deposit_balance', 'Deposit now, balance on completion'),
    )

    # --------------------------------------------------------
    # Parties
    # --------------------------------------------------------
    customer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='orders_as_customer'
    )
    provider = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='orders_as_provider'
    )
    service = models.ForeignKey(
        'services.Service', on_delete=models.SET_NULL, null=True, blank=True
    )
    selected_sample = models.ForeignKey(
        'services.ServicePortfolio',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="The portfolio image the client picked as their reference."
    )

    # --------------------------------------------------------
    # Job brief
    # --------------------------------------------------------
    title = models.CharField(max_length=200)
    description = models.TextField(
        help_text="What the client wants done."
    )
    materials_mode = models.CharField(
        max_length=20,
        choices=MATERIALS_MODE,
        default='fundi_provides'
    )
    materials_notes = models.TextField(
        blank=True, null=True,
        help_text="Details about the materials — types, quantity, condition."
    )

    # --------------------------------------------------------
    # Duration
    # --------------------------------------------------------
    estimated_days = models.IntegerField(
        null=True, blank=True,
        help_text="Fundi's estimate of how long the job will take."
    )

    # --------------------------------------------------------
    # Pricing & fees
    # --------------------------------------------------------
    agreed_price = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="The labour price agreed between client and fundi."
    )
    platform_fee = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="10% commission — deducted from fundi payout."
    )
    escrow_service_fee = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="3% customer-side escrow fee — added to invoice."
    )
    customer_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="agreed_price + escrow_service_fee."
    )
    deposit_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=30,
        help_text="Deposit percentage (default 30%)."
    )
    deposit_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Deposit = deposit_percent% of customer_total."
    )
    balance_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="customer_total - deposit_amount."
    )
    provider_payout = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="agreed_price - platform_fee."
    )

    # --------------------------------------------------------
    # Payment tracking
    # --------------------------------------------------------
    deposit_paid = models.BooleanField(default=False)
    deposit_payment_id = models.CharField(max_length=255, null=True, blank=True)
    deposit_paid_at = models.DateTimeField(null=True, blank=True)

    balance_paid = models.BooleanField(default=False)
    balance_payment_id = models.CharField(max_length=255, null=True, blank=True)
    balance_paid_at = models.DateTimeField(null=True, blank=True)

    # --------------------------------------------------------
    # Milestone (view/fit at 50%)
    # --------------------------------------------------------
    milestone_requested_at = models.DateTimeField(null=True, blank=True)
    milestone_viewed_at = models.DateTimeField(null=True, blank=True)

    # --------------------------------------------------------
    # Status & timing
    # --------------------------------------------------------
    status = models.CharField(
        max_length=25, choices=STATUS_CHOICES, default='pending_acceptance'
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    decline_reason = models.TextField(blank=True, null=True)
    cancel_reason = models.TextField(blank=True, null=True)

    # --------------------------------------------------------
    # Disclaimers
    # --------------------------------------------------------
    disclaimer_accepted = models.BooleanField(
        default=False,
        help_text="Client confirmed materials/designs supplied are at their own risk."
    )
    disclaimer_accepted_at = models.DateTimeField(null=True, blank=True)

    # --------------------------------------------------------
    # Timestamps
    # --------------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['provider', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"#{self.id} {self.title} — {self.customer.username} → {self.provider.username}"

    # --------------------------------------------------------
    # Fee math
    # --------------------------------------------------------
    def recalculate_fees(self, save=True):
        """Recompute fees, totals, deposit and balance from agreed_price."""
        from django.conf import settings

        platform_pct = Decimal(str(settings.PLATFORM_FEE_PERCENTAGE))
        escrow_pct = Decimal(str(settings.ESCROW_SERVICE_FEE_PERCENTAGE))

        self.platform_fee = (self.agreed_price * platform_pct / 100).quantize(Decimal('0.01'))
        self.escrow_service_fee = (self.agreed_price * escrow_pct / 100).quantize(Decimal('0.01'))
        self.customer_total = (self.agreed_price + self.escrow_service_fee).quantize(Decimal('0.01'))
        self.provider_payout = (self.agreed_price - self.platform_fee).quantize(Decimal('0.01'))
        self.deposit_amount = (self.customer_total * self.deposit_percent / 100).quantize(Decimal('0.01'))
        self.balance_amount = (self.customer_total - self.deposit_amount).quantize(Decimal('0.01'))

        if save:
            self.save(update_fields=[
                'platform_fee', 'escrow_service_fee', 'customer_total',
                'provider_payout', 'deposit_amount', 'balance_amount',
                'updated_at'
            ])

    # --------------------------------------------------------
    # Status helpers
    # --------------------------------------------------------
    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def is_active(self):
        return self.status not in ['completed', 'cancelled', 'declined', 'disputed']

    # Permissions
    def can_be_viewed_by(self, user):
        return user in [self.customer, self.provider] or user.is_staff

    def can_accept(self, user):
        return user == self.provider and self.status == 'pending_acceptance'

    def can_decline(self, user):
        return user == self.provider and self.status == 'pending_acceptance'

    def can_cancel(self, user):
        return user == self.customer and self.status in [
            'pending_acceptance', 'accepted'
        ]

    def can_pay_deposit(self, user):
        return (
            user == self.customer
            and self.status == 'accepted'
            and not self.deposit_paid
        )

    def can_start(self, user):
        return user == self.provider and self.status == 'deposit_paid'

    def can_request_milestone(self, user):
        return user == self.provider and self.status == 'in_progress'

    def can_view_milestone(self, user):
        return user == self.customer and self.status == 'milestone_ready'

    def can_submit(self, user):
        return user == self.provider and self.status in [
            'in_progress', 'milestone_ready'
        ]

    def can_approve(self, user):
        return user == self.customer and self.status == 'submitted'

    def can_dispute(self, user):
        return user in [self.customer, self.provider] and self.status in [
            'deposit_paid', 'in_progress', 'milestone_ready', 'submitted'
        ]

    def accept(self, user):
        if not self.can_accept(user):
            return False
        self.status = 'accepted'
        self.accepted_at = timezone.now()
        self.save()
        return True

    def decline(self, user, reason=''):
        if not self.can_decline(user):
            return False
        self.status = 'declined'
        self.declined_at = timezone.now()
        self.decline_reason = reason
        self.save()
        return True

    def cancel(self, user, reason=''):
        if not self.can_cancel(user):
            return False
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancel_reason = reason
        self.save()
        return True


class OrderLineItem(models.Model):
    """
    A line in the order quotation — e.g. "Oak wood, 5kg, KSh 200/kg".
    Used to build the invoice / quote PDF.
    """

    PROVIDED_BY = (
        ('fundi', 'Fundi provides'),
        ('client', 'Client provides'),
    )

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='line_items'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)

    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit = models.CharField(max_length=30, blank=True, default='piece')
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    provided_by = models.CharField(
        max_length=10, choices=PROVIDED_BY, default='fundi'
    )

    order_index = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order_index', 'id']

    def __str__(self):
        return f"{self.title} × {self.quantity} {self.unit}"

    def save(self, *args, **kwargs):
        self.line_total = (self.quantity * self.unit_price).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)


class OrderInspiration(models.Model):
    """
    Client-uploaded design inspiration (up to 3 images).
    These are references only, not materials, and are provided at
    the client's own risk.
    """

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='inspirations'
    )
    image = CloudinaryField('image', folder='order_inspiration', blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Inspiration for Order #{self.order.id}"


class OrderStatusLog(models.Model):
    """Every state transition on an order — for full audit trail."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='status_logs'
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    from_status = models.CharField(max_length=25, blank=True)
    to_status = models.CharField(max_length=25)
    note = models.TextField(blank=True, null=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order.id}: {self.from_status} → {self.to_status}"