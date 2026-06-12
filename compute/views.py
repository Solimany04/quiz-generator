from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from .models import UserComputeNode
from quizzes.models import QuizRequest, GeneratedQuiz
from .serializers import HeartbeatSerializer, TaskSerializer, TaskCompleteSerializer
import logging

logger = logging.getLogger(__name__)

def get_node_from_api_key(api_key):
    try:
        return UserComputeNode.objects.get(api_key=api_key, is_active=True)
    except UserComputeNode.DoesNotExist:
        return None

class HeartbeatView(APIView):
    def post(self, request):
        serializer = HeartbeatSerializer(data=request.data)
        if serializer.is_valid():
            node = get_node_from_api_key(serializer.validated_data['api_key'])
            if node:
                node.last_heartbeat = timezone.now()
                node.save()
                return Response({'status': 'ok'})
            return Response({'error': 'Invalid API Key'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TaskPollView(APIView):
    def get(self, request):
        api_key = request.headers.get('X-API-Key') or request.query_params.get('api_key')
        if not api_key:
            return Response({'error': 'Missing API Key'}, status=status.HTTP_401_UNAUTHORIZED)
        
        node = get_node_from_api_key(api_key)
        if not node:
            return Response({'error': 'Invalid API Key'}, status=status.HTTP_401_UNAUTHORIZED)

        # Find a task waiting for this specific node
        task = QuizRequest.objects.filter(
            status='WAITING_FOR_NODE',
            processed_by_node=node
        ).first()

        if task:
            task.status = 'DISPATCHED_TO_NODE'
            task.save()
            serializer = TaskSerializer(task)
            return Response(serializer.data)
            
        return Response({'message': 'No pending tasks'}, status=status.HTTP_204_NO_CONTENT)

class TaskCompleteView(APIView):
    def post(self, request, task_id):
        serializer = TaskCompleteSerializer(data=request.data)
        if serializer.is_valid():
            node = get_node_from_api_key(serializer.validated_data['api_key'])
            if not node:
                return Response({'error': 'Invalid API Key'}, status=status.HTTP_401_UNAUTHORIZED)
                
            try:
                task = QuizRequest.objects.get(id=task_id, processed_by_node=node, status='DISPATCHED_TO_NODE')
            except QuizRequest.DoesNotExist:
                return Response({'error': 'Task not found or not assigned to this node'}, status=status.HTTP_404_NOT_FOUND)

            # Process the returned quizzes
            results = serializer.validated_data['results']
            
            # Save generated quizzes
            for quiz_data in results:
                GeneratedQuiz.objects.create(
                    request=task,
                    question=quiz_data.get('question', ''),
                    options=quiz_data.get('options', []),
                    correct_option_id=quiz_data.get('correct_option_id', 0),
                    explanation=quiz_data.get('explanation', '')
                )
            
            task.status = 'COMPLETED'
            task.save()
            
            node.total_processed_tasks += 1
            node.save()
            
            # Trigger dispatch to telegram celery task
            # from quizzes.tasks import dispatch_quiz_to_telegram
            # dispatch_quiz_to_telegram.delay(task.id)
            
            return Response({'status': 'Task marked completed'})
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
