from django.urls import path
from .views import classify_name

urlpatterns = [
    path('classify', classify_name),
]