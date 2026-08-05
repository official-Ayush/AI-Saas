from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('checkout/', views.create_checkout_session, name='checkout'),
    path('webhook/', views.gumroad_webhook, name='webhook'),
]