from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
import logging

from users.models import TelegramUser
from compute.models import UserComputeNode
from .models import QuizRequest
from .tasks import process_quiz_central

logger = logging.getLogger(__name__)

class TelegramWebhookView(APIView):
    def post(self, request):
        update = request.data
        if 'message' not in update:
            return Response({'status': 'ok'})

        message = update['message']
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text') or message.get('caption', '')
        
        # Simple filter based on original logic
        if "A)" not in text and "Question" not in text:
            return Response({'status': 'ignored'})

        from_user = message.get('from', {})
        telegram_id = from_user.get('id')
        username = from_user.get('username', '')

        # Get or create user
        user, _ = TelegramUser.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={'username': username}
        )

        # Check if user has an active BYOC node
        recent_threshold = timezone.now() - timedelta(minutes=5)
        node = UserComputeNode.objects.filter(
            user=user, 
            is_active=True,
            last_heartbeat__gte=recent_threshold
        ).first()

        quiz_request = QuizRequest.objects.create(
            user=user,
            raw_text=text,
            chat_id=str(chat_id)
        )

        if node:
            # Route to User Node
            quiz_request.status = 'WAITING_FOR_NODE'
            quiz_request.processed_by_type = 'USER_NODE'
            quiz_request.processed_by_node = node
            quiz_request.save()
            logger.info(f"Routed request {quiz_request.id} to user node {node.id}")
        else:
            # Route to Central Queue
            quiz_request.status = 'PENDING'
            quiz_request.processed_by_type = 'CENTRAL_GPU'
            quiz_request.save()
            process_quiz_central.delay(quiz_request.id)
            logger.info(f"Routed request {quiz_request.id} to central queue")

        return Response({'status': 'ok'})
