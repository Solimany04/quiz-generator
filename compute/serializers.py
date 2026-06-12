from rest_framework import serializers
from .models import UserComputeNode
from quizzes.models import QuizRequest

class HeartbeatSerializer(serializers.Serializer):
    api_key = serializers.UUIDField()

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizRequest
        fields = ['id', 'raw_text']

class TaskCompleteSerializer(serializers.Serializer):
    api_key = serializers.UUIDField()
    results = serializers.ListField(
        child=serializers.JSONField(),
        allow_empty=False
    )
