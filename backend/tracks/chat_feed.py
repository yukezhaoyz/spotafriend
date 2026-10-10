"""Live chat between two people over AWS AppSync Events.

The browser talks to AppSync directly over a WebSocket: it subscribes to
channels and publishes to them, so messages arrive the moment they're sent.
Django hands each page the API's endpoints and key (see browser_config), and
publishes one event itself: the MATCH announcement when a playlist is imported.

Channels, all in the SPOTAFRIEND_APPSYNC_NAMESPACE namespace ("chat"):
  /chat/requests        "Start chat" posts a CHAT_REQUEST ("<name> wants to
                        chat with you") here; every open main page hears it.
  /chat/matches         importing a playlist posts a MATCH here with a new room
                        id; every open main page (the importer's too) can
                        open that room from its bell.
  /chat/rooms/<room>    one per chat; CHAT_MESSAGE events, plus HELLO/HISTORY
                        so someone who joins late gets the messages they missed.

Nothing is stored in the database or in AWS: a chat lasts as long as one of
its pages is open. `manage.py appsync_setup` creates the API and prints the
settings for .env.
"""
import json
import logging
import os
import time
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

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


# Publishing happens in the background so a slow AWS call never delays an import.
_executor = ThreadPoolExecutor(max_workers=2)


def _post(channel, event):
    req = urllib.request.Request(
        f"https://{HTTP_DOMAIN}/event",
        data=json.dumps({"channel": channel, "events": [json.dumps(event)]}).encode(),
        headers={"content-type": "application/json", "x-api-key": API_KEY},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            failed = json.loads(resp.read() or b"{}").get("failed")
            if failed:
                logger.error("AppSync rejected the event on %s: %s", channel, failed)
    except Exception:
        logger.exception("Publishing to AppSync channel %s failed", channel)


def announce_match(user, match, client_id):
    """Post "<name> has a match with <match>" to /chat/matches with a new chat
    room, in the background. Returns the event, or None while live chat is off."""
    if not available():
        return None
    event = {
        "type": "MATCH",
        "id": str(uuid.uuid4()),
        "clientId": client_id,
        "roomId": str(uuid.uuid4()),
        "fromName": user.name,
        "matchName": match["name"],
        "score": round(match["score"]),
        "message": f"{user.name} has a match with {match['name']}!",
        "sentAtMs": int(time.time() * 1000),
    }
    _executor.submit(_post, f"/{NAMESPACE}/matches", event)
    return event
