# api/urls.py
from django.urls import path
from .views import ClassifyMessageView, health_check

urlpatterns = [
    # This root path now points to your health check view
    path('', health_check, name='health-check'),
    
    # This is your existing API endpoint
    path('classify/', ClassifyMessageView.as_view(), name='classify-message'),
]