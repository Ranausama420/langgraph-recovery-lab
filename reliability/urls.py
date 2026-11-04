from django.urls import include, path
from .health import health
urlpatterns = [path("api/", include("jobs.urls")), path("health/", health)]
