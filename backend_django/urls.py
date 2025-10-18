# core/urls.py (or your_project_name/urls.py)
# CORRECT
from django.urls import path, include
from django.contrib import admin
from django.urls import path, include # Make sure to import 'include'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')), # Add this line
]