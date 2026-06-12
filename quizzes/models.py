from django.db import models
from django.conf import settings
from compute.models import UserComputeNode

class QuizRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('WAITING_FOR_NODE', 'Waiting For Node'),
        ('DISPATCHED_TO_NODE', 'Dispatched To Node'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )

    PROCESSED_BY_CHOICES = (
        ('CENTRAL_GPU', 'Central GPU'),
        ('USER_NODE', 'User Node'),
        ('UNASSIGNED', 'Unassigned')
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_requests')
    raw_text = models.TextField()
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='PENDING')
    processed_by_type = models.CharField(max_length=20, choices=PROCESSED_BY_CHOICES, default='UNASSIGNED')
    processed_by_node = models.ForeignKey(UserComputeNode, null=True, blank=True, on_delete=models.SET_NULL)
    chat_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Request {self.id} - {self.status}"

class GeneratedQuiz(models.Model):
    request = models.ForeignKey(QuizRequest, on_delete=models.CASCADE, related_name='generated_quizzes')
    question = models.TextField()
    options = models.JSONField() # List of strings
    correct_option_id = models.IntegerField()
    explanation = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Quiz for Request {self.request.id}"
