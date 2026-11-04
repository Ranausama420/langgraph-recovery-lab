import os
import sys
from urllib.parse import urlparse
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "local-development-only")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [host for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host]
INSTALLED_APPS = ["django.contrib.contenttypes", "django.contrib.auth", "corsheaders", "rest_framework", "jobs"]
MIDDLEWARE = ["corsheaders.middleware.CorsMiddleware"]
ROOT_URLCONF = "reliability.urls"
database_url = os.getenv("DATABASE_URL", "")
if database_url.startswith(("postgres://", "postgresql://")):
    parsed_database = urlparse(database_url)
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed_database.path.removeprefix("/"),
        "USER": parsed_database.username,
        "PASSWORD": parsed_database.password,
        "HOST": parsed_database.hostname,
        "PORT": parsed_database.port or 5432,
    }}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
REST_FRAMEWORK = {"UNAUTHENTICATED_USER": None}
CORS_ALLOWED_ORIGINS = [origin for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin]
ASYNC_JOBS = os.getenv("PULSEOPS_ASYNC_JOBS", "false").lower() == "true"
TESTING = "test" in sys.argv
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_TRACK_STARTED = True
