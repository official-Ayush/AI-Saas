import os
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from huggingface_hub import InferenceClient
from .models import AIGeneration, User

# Initialize Hugging Face Inference Client
HF_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
client = InferenceClient(
    model=HF_MODEL,
    token=os.environ.get("HF_TOKEN")
)


def landing_page(request):
    """
    Renders the public landing page.
    """
    return render(request, 'saas_app/landing.html')


def signup_view(request):
    """
    Handles new user registration and awards 5 free credits.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    error_message = None

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        if password != password_confirm:
            error_message = "Passwords do not match."
        elif User.objects.filter(username=username).exists():
            error_message = "Username is already taken."
        else:
            # Create user and give 5 free credits
            user = User.objects.create_user(username=username, email=email, password=password)
            user.credits = 5
            user.tier = 'FREE'
            user.save()

            # Auto-login after registration
            login(request, user)
            return redirect('dashboard')

    return render(request, 'saas_app/signup.html', {'error_message': error_message})


def login_view(request):
    """
    Handles user login.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    error_message = None

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
        else:
            error_message = "Invalid username or password."

    return render(request, 'saas_app/login.html', {'error_message': error_message})


def logout_view(request):
    """
    Logs out the user and redirects to the landing page.
    """
    logout(request)
    return redirect('landing')


@login_required
def dashboard(request):
    user = request.user
    ai_result = None
    error_message = None

    if request.method == "POST":
        prompt = request.POST.get("prompt")
        
        if user.credits > 0:
            try:
                response = client.chat_completion(
                    messages=[
                        {"role": "system", "content": "You are a helpful AI assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500
                )
                ai_result = response.choices[0].message.content
                
                user.credits -= 1
                user.save()
                
                AIGeneration.objects.create(
                    user=user,
                    prompt=prompt,
                    result=ai_result,
                    credits_cost=1
                )
            except Exception as e:
                error_message = f"Hugging Face API Error: {str(e)}"
        else:
            error_message = "You are out of credits! Please purchase more credits to continue."

    history = AIGeneration.objects.filter(user=user).order_by('-created_at')[:5]

    context = {
        'tier': user.tier,
        'credits': user.credits,
        'history': history,
        'ai_result': ai_result,
        'error_message': error_message,
    }
    return render(request, 'saas_app/dashboard.html', context)


@login_required
def create_checkout_session(request):
    """
    Redirects the user to your Gumroad checkout page.
    """
    gumroad_url = "https://gumroad.com/l/YOUR_LINK_HERE" 
    checkout_url = f"{gumroad_url}?user_id={request.user.id}"
    return redirect(checkout_url)


@csrf_exempt
def gumroad_webhook(request):
    """
    Handles incoming webhook notifications from Gumroad.
    """
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                user.tier = 'PRO'
                user.credits += 100
                user.save()
                return HttpResponse("Credits added successfully!", status=200)
            except User.DoesNotExist:
                return HttpResponse("User not found", status=404)
                
    return HttpResponse("Method not allowed", status=405)