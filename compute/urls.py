from django.urls import path
from .views import HeartbeatView, TaskPollView, TaskCompleteView

urlpatterns = [
    path('heartbeat/', HeartbeatView.as_view(), name='worker-heartbeat'),
    path('tasks/', TaskPollView.as_view(), name='worker-tasks-poll'),
    path('tasks/<int:task_id>/complete/', TaskCompleteView.as_view(), name='worker-tasks-complete'),
]
