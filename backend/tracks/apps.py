import os
import sys

from django.apps import AppConfig


class TracksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tracks"

    def ready(self):
        # runserver's autoreloader starts a parent watcher process plus a child
        # that serves requests (RUN_MAIN=true). Only the child needs the data.
        if "runserver" in sys.argv and "--noreload" not in sys.argv and not os.environ.get("RUN_MAIN"):
            return
        from .loader import load_dataset
        load_dataset()
