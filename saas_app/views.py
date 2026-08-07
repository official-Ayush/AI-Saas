import os
import json
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, StreamingHttpResponse, JsonResponse
from huggingface_hub import InferenceClient
from .models import AIGeneration, User

# Initialize Hugging Face Inference Client
HF_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
client = InferenceClient(
    model=HF_MODEL,
    token=os.environ.get("HF_TOKEN")
)


def landing_page(request):
    return render(request, 'saas_app/landing.html')


def signup_view(request):
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
            user = User.objects.create_user(username=username, email=email, password=password)
            user.credits = 5
            user.tier = 'FREE'
            user.save()
            login(request, user)
            return redirect('dashboard')

    return render(request, 'saas_app/signup.html', {'error_message': error_message})


def login_view(request):
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
    logout(request)
    return redirect('landing')


@login_required
def dashboard(request):
    """
    Renders the dashboard UI. (AI generation is now handled via AJAX).
    """
    user = request.user
    history = AIGeneration.objects.filter(user=user).order_by('-created_at')[:5]

    context = {
        'tier': user.tier,
        'credits': user.credits,
        'history': history,
    }
    return render(request, 'saas_app/dashboard.html', context)


@login_required
def stream_generate(request):
    """
    API Endpoint that streams the AI response chunk-by-chunk back to the browser.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            prompt = data.get("prompt")
            user = request.user

            # Check credits before generating
            if user.credits <= 0:
                return JsonResponse({"error": "You are out of credits! Please upgrade to continue."}, status=402)

            def generate_stream():
                full_text = ""
                try:
                    # Request the stream from Hugging Face
                    stream = client.chat_completion(
                        messages=[
                            {"role": "system", "content": "You are a helpful AI assistant. Format your responses in clean Markdown."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=800,
                        stream=True  # Tells HF to stream the response
                    )
                    
                    # Yield chunks as they arrive
                    for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            text_chunk = chunk.choices[0].delta.content
                            full_text += text_chunk
                            yield text_chunk
                    
                    # Once the stream is entirely finished, deduct the credit and save history
                    if full_text:
                        user.credits -= 1
                        user.save()
                        AIGeneration.objects.create(
                            user=user,
                            prompt=prompt,
                            result=full_text,
                            credits_cost=1
                        )
                except Exception as e:
                    yield f"\n\n**API Error:** {str(e)}"

            # Return a Django Streaming Response
            return StreamingHttpResponse(generate_stream(), content_type='text/plain')
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
            
    return JsonResponse({"error": "Invalid request method"}, status=405)


@login_required
def create_checkout_session(request):
    gumroad_url = "https://gumroad.com/l/YOUR_LINK_HERE" 
    checkout_url = f"{gumroad_url}?user_id={request.user.id}"
    return redirect(checkout_url)


@csrf_exempt
def gumroad_webhook(request):
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

@login_required
def optimize_prompt(request):
    """
    Takes a rough user prompt and uses AI to rewrite it into an expert-level prompt.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            raw_prompt = data.get("prompt")
            
            if not raw_prompt or len(raw_prompt) < 3:
                return JsonResponse({"error": "Please type a few words first!"}, status=400)

            # System prompt instructing the AI to act as a prompt engineer
            system_msg = "You are an expert AI prompt engineer. The user will give you a basic idea. Rewrite it into a highly detailed, professional, and clear prompt. Do not answer the prompt itself. Just provide the improved prompt text. Do not include quotes or intro text."
            
            response = client.chat_completion(
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": f"Optimize this: {raw_prompt}"}
                ],
                max_tokens=200
            )
            
            optimized_text = response.choices[0].message.content.strip()
            
            # Remove leading/trailing quotes if the AI adds them
            if optimized_text.startswith('"') and optimized_text.endswith('"'):
                optimized_text = optimized_text[1:-1]

            return JsonResponse({"optimized_prompt": optimized_text})
            
        except Exception as e:
            return JsonResponse({"error": "Failed to optimize."}, status=400)
            
    return JsonResponse({"error": "Invalid request method"}, status=405)