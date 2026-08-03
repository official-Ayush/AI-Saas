import os
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import AIGeneration
from huggingface_hub import InferenceClient

# Initialize Hugging Face Inference Client with a chosen model
# (e.g., Meta Llama 3.1 8B, Qwen 2.5, or Mistral 7B)
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
                # 1. Call Hugging Face Chat Completion
                response = client.chat_completion(
                    messages=[
                        {"role": "system", "content": "You are a helpful AI assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500
                )
                
                # Extract the response text
                ai_result = response.choices[0].message.content
                
                # 2. Deduct credit & save to database
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
            error_message = "You are out of credits! Please upgrade to Pro."

    history = AIGeneration.objects.filter(user=user).order_by('-created_at')[:5]

    context = {
        'tier': user.tier,
        'credits': user.credits,
        'history': history,
        'ai_result': ai_result,
        'error_message': error_message,
    }
    
    return render(request, 'saas_app/dashboard.html', context)