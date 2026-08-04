import os
import json
import hmac
import hashlib
import urllib.parse
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
                
                # Deduct credit and save
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
    Redirects the user to your Lemon Squeezy checkout page.
    """
    # Replace 'ribhuai' with your actual Lemon Squeezy store subdomain if different
    store_url = "https://ribhuai.lemonsqueezy.com/checkout/buy"
    
    # Replace with your actual Variant ID from Lemon Squeezy product settings
    variant_id = "YOUR_VARIANT_ID_HERE" 
    
    custom_data = {
        "checkout[custom][user_id]": request.user.id
    }
    
    query_string = urllib.parse.urlencode(custom_data)
    checkout_url = f"{store_url}/{variant_id}?{query_string}"
    
    return redirect(checkout_url)


@csrf_exempt
def lemon_squeezy_webhook(request):
    """
    Handles incoming webhook notifications from Lemon Squeezy.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    webhook_secret = os.environ.get("LEMON_SQUEEZY_WEBHOOK_SECRET", "")
    secret = webhook_secret.encode('utf-8')
    signature = request.META.get('HTTP_X_SIGNATURE', '')
    
    digest = hmac.new(secret, request.body, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(digest, signature):
        return HttpResponse("Invalid signature", status=400)

    try:
        payload = json.loads(request.body)
        event_name = payload.get('meta', {}).get('event_name')
        
        if event_name == 'order_created':
            custom_data = payload.get('meta', {}).get('custom_data', {})
            user_id = custom_data.get('user_id')
            
            if user_id:
                user = User.objects.get(id=user_id)
                user.tier = 'PRO'
                user.credits += 100
                user.save()

        return HttpResponse(status=200)

    except Exception as e:
        return HttpResponse(f"Webhook Error: {str(e)}", status=400)