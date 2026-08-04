from django.urls import path
from django.shortcuts import redirect
from . import views

urlpatterns = [
    path('', lambda request: redirect('dashboard')),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('checkout/', views.create_checkout_session, name='checkout'),
    path('webhook/', views.lemon_squeezy_webhook, name='webhook'),
]