# api/urls.py
from django.urls import path
from .views import ClassifyMessageView

urlpatterns = [
    path('classify/', ClassifyMessageView.as_view(), name='classify-message'),
]