import json
import httpx
from celery import shared_task
from django.conf import settings
from .models import QuizRequest, GeneratedQuiz
from llm.models import ModelRegistry
import re
import logging

logger = logging.getLogger(__name__)

LM_STUDIO_API_URL = 'http://localhost:1234/v1/chat/completions'
SYSTEM_PROMPT = """You are a precise data converter. Your task is to convert plain text quizzes/polls into a valid JSON array matching the required schema.

Schema:
[
  {
    "question": "Question text",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_option_id": 0,
    "explanation": "Explanation/Rationale text"
  }
]

Rules:
1. Do NOT include any conversational text or markdown formatting. Output ONLY raw, valid JSON.
2. Options must have any leading letter markers (like "A) ", "B. ") stripped.
3. Map the correct answer letter to the correct 0-indexed integer.
4. If the input contains multiple questions, you MUST return an array containing a JSON object for EACH question.
"""

@shared_task(bind=True, max_retries=3)
def process_quiz_central(self, request_id):
    try:
        quiz_request = QuizRequest.objects.get(id=request_id)
        if quiz_request.status != 'PENDING' or quiz_request.processed_by_type != 'CENTRAL_GPU':
            return
            
        text = quiz_request.raw_text
        chunks = re.split(r'(?i)(?=\bQuestion\s*\d*\b)', text)
        all_polls = []

        # Find default active model
        default_model = ModelRegistry.objects.filter(is_active_default=True).first()
        model_name = default_model.model_identifier if default_model else "google/gemma-4-e2b"

        with httpx.Client(timeout=60) as client:
            for i, chunk in enumerate(chunks):
                chunk = chunk.strip()
                if not chunk or len(chunk) < 15:
                    continue
                    
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": chunk}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 4096
                }
                
                response = client.post(LM_STUDIO_API_URL, json=payload)
                response.raise_for_status()
                result = response.json()
                
                raw_json_str = result['choices'][0]['message']['content'].strip()
                if raw_json_str.startswith("```json"):
                    raw_json_str = raw_json_str[7:]
                if raw_json_str.endswith("```"):
                    raw_json_str = raw_json_str[:-3]
                    
                try:
                    polls = json.loads(raw_json_str.strip())
                    if isinstance(polls, dict):
                        all_polls.append(polls)
                    elif isinstance(polls, list):
                        all_polls.extend(polls)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON for chunk {i}")

        if all_polls:
            for poll in all_polls:
                GeneratedQuiz.objects.create(
                    request=quiz_request,
                    question=poll.get("question", ""),
                    options=poll.get("options", []),
                    correct_option_id=poll.get("correct_option_id", 0),
                    explanation=poll.get("explanation", "")
                )
            quiz_request.status = 'COMPLETED'
            quiz_request.save()
            
            # Dispatch back to telegram
            dispatch_quiz_to_telegram.delay(quiz_request.id)
            
        else:
            quiz_request.status = 'FAILED'
            quiz_request.save()

    except Exception as exc:
        quiz_request.status = 'FAILED'
        quiz_request.save()
        logger.error(f"Failed central processing: {exc}")
        self.retry(exc=exc, countdown=60)

@shared_task(rate_limit='20/m')
def dispatch_quiz_to_telegram(request_id):
    try:
        import os
        quiz_request = QuizRequest.objects.get(id=request_id)
        if quiz_request.status != 'COMPLETED' or not quiz_request.chat_id:
            return
            
        quizzes = quiz_request.generated_quizzes.all()
        logger.info(f"Dispatching {quizzes.count()} quizzes to chat {quiz_request.chat_id}")
        
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN not set, cannot dispatch.")
            return

        url = f"https://api.telegram.org/bot{token}/sendPoll"
        
        with httpx.Client(timeout=10) as client:
            for quiz in quizzes:
                payload = {
                    "chat_id": quiz_request.chat_id,
                    "question": quiz.question,
                    "options": json.dumps(quiz.options),
                    "type": "quiz",
                    "is_anonymous": True,
                    "correct_option_id": quiz.correct_option_id
                }
                if quiz.explanation:
                    payload["explanation"] = quiz.explanation
                    
                resp = client.post(url, data=payload)
                if resp.status_code != 200:
                    logger.error(f"Failed to post quiz: {resp.text}")
                else:
                    logger.info(f"Successfully dispatched quiz {quiz.id}")

    except Exception as e:
        logger.error(f"Error dispatching quiz: {e}")
