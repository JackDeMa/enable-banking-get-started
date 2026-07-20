# callbacks/urls.py
from django.urls import path

from .views import enable_banking_callback

urlpatterns = [
    path("callback", enable_banking_callback),
]