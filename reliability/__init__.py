try:
    from .celery import app as celery_app
except ImportError:  # Celery is optional for the synchronous local demo.
    celery_app = None

__all__ = ("celery_app",)
