# services/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from cloudinary.models import CloudinaryField

User = get_user_model()

class ServiceCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Service Categories'
    
    def __str__(self):
        return self.name


class Service(models.Model):
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services')
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='services')
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    price_min = models.DecimalField(max_digits=12, decimal_places=2)
    price_max = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Deposit settings
    deposit_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=30,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    delivery_time_days = models.IntegerField(default=7)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    views = models.IntegerField(default=0)
    orders_completed = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def calculate_deposit(self, amount):
        """Calculate deposit amount based on percentage"""
        return (amount * self.deposit_percentage) / 100


class ServicePortfolio(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='portfolio')
    
    # Using CloudinaryField for portfolio images
    image = CloudinaryField(
        'image',
        folder='portfolio',
        blank=True,
        null=True
    )
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_cover = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_cover', '-created_at']
    
    def __str__(self):
        return f"{self.service.title} - {self.title}"