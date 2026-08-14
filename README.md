# SitePulse Django

Public Django integration package for SitePulse first-party analytics.

This package is installed into a customer Django app. It does not include the private SitePulse central dashboard/server. It sends signed events to the central SitePulse ingest API that you configure.

## Install

```bash
pip install "git+https://github.com/YOUR_ORG/sitepulse-django.git"
```

Pin a commit in production:

```bash
pip install "git+https://github.com/YOUR_ORG/sitepulse-django.git@COMMIT_SHA"
```

## Configure Django

```python
INSTALLED_APPS += ["sitepulse.django"]

MIDDLEWARE += [
    "sitepulse.django.middleware.SitePulseMiddleware",
]

SITEPULSE = {
    "PROJECT_ID": "project-id-from-sitepulse",
    "SECRET": "project-secret-from-sitepulse",
    "INGEST_URL": "https://sitepulse.example.com/api/v1/ingest/",
    "PUBLIC_EVENT_PATH": "api/runtime/events/",
    "COOKIE_NAME": "_rtid",
    "DELIVERY_MODE": "database_outbox",
    "FINGERPRINT_LEVEL": "basic",
}
```

```python
from django.urls import include, path

urlpatterns += [
    path("api/runtime/", include("sitepulse.django.urls")),
]
```

Run migrations if using `database_outbox`:

```bash
python manage.py migrate
```

Run the outbox worker:

```bash
python manage.py drain_sitepulse_outbox --loop --sleep 2
```

## Browser SDK

The package ships the runtime as Django static content.

```django
{% load static %}
<script src="{% static 'sitepulse/runtime-core.js' %}"></script>
<script>
RuntimeCore.init({
  endpoint: "/api/runtime/events/",
  automaticPageViews: true,
  captureClicks: true,
  captureErrors: true,
  captureWebVitals: true,
  fingerprintLevel: "basic"
})
</script>
```

## Architecture

```text
Browser
  -> customer Django app /api/runtime/events/
  -> sitepulse.django signs and queues/sends the batch
  -> private SitePulse central server /api/v1/ingest/
```
