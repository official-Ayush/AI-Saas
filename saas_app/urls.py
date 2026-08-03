from django.urls import path
from django.shortcuts import redirect # <-- Add this import
from . import views

urlpatterns = [
    # 1. Add this new line to redirect the root domain to the dashboard
    path('', lambda request: redirect('dashboard')), 
    
    # Your existing paths:
    path('dashboard/', views.dashboard, name='dashboard'),
    path('checkout/', views.create_checkout_session, name='checkout'),
    path('webhook/', views.lemon_squeezy_webhook, name='webhook'), 
]