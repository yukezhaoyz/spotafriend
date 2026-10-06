"""Django settings for the Spotafriend backend (local hackathon demo)."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_CSV = BASE_DIR.parent / "dataset.csv"

SECRET_KEY = "dev-only-not-secret"
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "tracks",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
    }
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# Named, shared-cache in-memory SQLite DB: every thread/connection in the
# process sees the same data. It lives only as long as the process does and
# is rebuilt from dataset.csv on each start (see tracks/loader.py).
IN_MEMORY_DB_URI = "file:spotafriend?mode=memory&cache=shared"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": IN_MEMORY_DB_URI,
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
