"""Django settings for the Spotafriend backend (local hackathon demo)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(path):
    """Read KEY=VALUE lines from the repo's .env file (see .env.example).
    Values already set in the terminal win over the file, and blank values
    count as not set."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip("'\"")
        if value:
            os.environ.setdefault(key.strip(), value)


_load_env_file(BASE_DIR.parent / ".env")
DATASET_CSV = BASE_DIR.parent / "dataset.csv"

SECRET_KEY = "dev-only-not-secret"
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "tracks",
]

MIDDLEWARE = [
    "tracks.middleware.OneRequestAtATimeMiddleware",
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
