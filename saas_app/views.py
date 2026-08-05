import os
from django.shortcuts import render, redirect
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