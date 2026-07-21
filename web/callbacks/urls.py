# callbacks/urls.py
from django.urls import path

from .views import connection_success, enable_banking_callback

urlpatterns = [
    path("callback", enable_banking_callback),
    path(
        "connection/success",
        connection_success,
        name="connection-success",
    ),
]