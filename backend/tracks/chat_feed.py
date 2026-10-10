"""Live chat between two people over AWS AppSync Events.

The browser talks to AppSync directly over a WebSocket: it subscribes to
channels and publishes to them, so messages arrive the moment they're sent.
Django only hands each page the API's endpoints and key (see browser_config).

Channels, all in the SPOTAFRIEND_APPSYNC_NAMESPACE namespace ("chat"):
  /chat/requests        "Start chat" posts a CHAT_REQUEST ("<name> wants to
                        chat with you") here; every open main page hears it.
  /chat/matches         importing a playlist posts ARRIVED here; every page
                        whose person already imported answers with a MATCH
                        naming a new room, and both say "You've received a match!".
  /chat/announcements   the page that makes a new pair's room also posts
                        MATCHED here, so everyone else on the site hears
                        "<a> and <b> just matched!".
  /chat/rooms/<room>    one per chat; CHAT_MESSAGE events, plus HELLO/HISTORY
                        so someone who joins late gets the messages they missed.

Nothing is stored in the database or in AWS: a chat lasts as long as one of
its pages is open. `manage.py appsync_setup` creates the API and prints the
settings for .env.
"""
import os

HTTP_DOMAIN = os.environ.get("SPOTAFRIEND_APPSYNC_HTTP_DOMAIN", "")
REALTIME_DOMAIN = os.environ.get("SPOTAFRIEND_APPSYNC_REALTIME_DOMAIN", "")
API_KEY = os.environ.get("SPOTAFRIEND_APPSYNC_API_KEY", "")
NAMESPACE = os.environ.get("SPOTAFRIEND_APPSYNC_NAMESPACE", "chat")


def available():
    return bool(HTTP_DOMAIN and REALTIME_DOMAIN and API_KEY)


def browser_config():
    """What the page needs to connect, or None while live chat is off.

    The API key goes to the browser: anyone who can open the page can use it,
    which is fine for this local demo (rooms are random UUIDs) but not beyond."""
    if not available():
        return None
    return {"httpDomain": HTTP_DOMAIN, "realtimeDomain": REALTIME_DOMAIN, "apiKey": API_KEY, "namespace": NAMESPACE}
