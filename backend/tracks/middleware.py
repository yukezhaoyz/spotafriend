import threading

_db_lock = threading.Lock()


class OneRequestAtATimeMiddleware:
    """Handle requests one after another.

    The in-memory SQLite database is shared between the server's threads in
    "shared cache" mode, where two threads writing at once fail right away
    with "database table is locked" instead of waiting. The page checks in
    every couple of seconds, so that collision is common. Requests here take
    milliseconds, so queueing them costs nothing noticeable for a local demo.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with _db_lock:
            return self.get_response(request)
