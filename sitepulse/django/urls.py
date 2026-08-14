from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path("events/", views.events, name="sitepulse_events"),
]
