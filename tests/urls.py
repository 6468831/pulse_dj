from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("api/runtime/", include("sitepulse.django.urls")),
]
