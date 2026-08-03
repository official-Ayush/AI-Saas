from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser

# 1. The Custom User Model
class User(AbstractUser):
    """
    Overrides the default Django user to add SaaS and payment fields.
    """
    TIER_CHOICES = (
        ('FREE', 'Free Tier'),
        ('PRO', 'Pro Tier'),
    )
    
    # Subscription & Billing
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, default='FREE')
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    
    # AI Usage
    credits = models.IntegerField(default=5) # New users get 5 free credits

    def __str__(self):
        return self.username

# 2. The AI Generation History Model
class AIGeneration(models.Model):
    """
    Logs every time a user generates something with the AI.
    """
    # If a user is deleted, delete their generations too (CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='generations')
    
    # The data
    prompt = models.TextField(help_text="What the user asked the AI")
    result = models.TextField(blank=True, null=True, help_text="The AI's response")
    credits_cost = models.IntegerField(default=1)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} | {self.created_at.strftime('%Y-%m-%d')}"