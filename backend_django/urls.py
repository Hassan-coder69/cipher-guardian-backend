from django.contrib import admin
from django.urls import path, include # Make sure 'include' is imported

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # This line tells Django to send any request that starts with ''
    # to be handled by the urls.py file inside your 'api' app.
    # This is how your health check at the root path will be found.
    path('', include('api.urls')),
]
