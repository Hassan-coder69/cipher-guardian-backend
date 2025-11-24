from django.urls import path
from .views import ClassifyTextView, ClassifyMessageView, health_check, generate_overview

urlpatterns = [
    path('', health_check, name='health_check'),
    path('classify-text/', ClassifyTextView.as_view(), name='classify_text'),  # NEW: For frontend
    path('classify/', ClassifyMessageView.as_view(), name='classify_message'),  # LEGACY: For Cloud Function
    path('generate-overview/', generate_overview, name='generate_overview'),
]