from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # New route for the AJAX stream
    path('stream/', views.stream_generate, name='stream_generate'), 
    
    path('checkout/', views.create_checkout_session, name='checkout'),
    path('webhook/', views.gumroad_webhook, name='webhook'),
    path('optimize/', views.optimize_prompt, name='optimize_prompt'),
]