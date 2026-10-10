import json
import os
import sqlite3

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import chat, chat_feed, email_alerts, matching, notifications, seed
from .playlists import PlaylistNotFound, fetch_playlist, normalize_playlist_url, track_ids_from_payload
from .loader import run_readonly_sql
from .models import Conversation, MockPlaylist, Notification, Track, User, UserTrack

MAX_ROWS = 1000


@require_GET
def schema(request):
    columns, rows, _ = run_readonly_sql("SELECT name, type FROM pragma_table_info('tracks')")
    return JsonResponse({
        "table": "tracks",
        "row_count": Track.objects.count(),
        "columns": [{"name": n, "type": t} for n, t in rows],
    })


@csrf_exempt
@require_POST
def query(request):
    """POST {"sql": "SELECT ...", "params": [...]} -> rows. Read-only."""
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Body must be JSON"}, status=400)
    sql = body.get("sql")
    if not sql:
        return JsonResponse({"error": "Missing 'sql'"}, status=400)
    try:
        columns, rows, truncated = run_readonly_sql(sql, body.get("params", []), max_rows=MAX_ROWS)
    except sqlite3.Error as e:
        return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({
        "columns": columns,
        "rows": [dict(zip(columns, r)) for r in rows],
        "row_count": len(rows),
        "truncated": truncated,
    })


@require_GET
def track_list(request):
    """ORM-backed lookup: ?genre=&artist=&q=&limit="""
    qs = Track.objects.all()
    if genre := request.GET.get("genre"):
        qs = qs.filter(track_genre=genre)
    if artist := request.GET.get("artist"):
        qs = qs.filter(artists__icontains=artist)
    if q := request.GET.get("q"):
        qs = qs.filter(track_name__icontains=q)
    limit = min(int(request.GET.get("limit", 50)), MAX_ROWS)
    return JsonResponse({"tracks": list(qs.order_by("-popularity").values()[:limit])})


def _profile_json(user):
    p = user.profile
    return {
        "id": user.pk,
        "name": user.name,
        "track_count": p.track_count,
        "matched_count": p.matched_count,
        "coverage": round(p.matched_count / p.track_count, 3) if p.track_count else 0,
        "features": {f: getattr(p, f) for f in matching.FEATURES},
    }


@csrf_exempt
def users(request):
    """GET: list users. POST {"name": "...", "track_ids": [...]} or
    {"name": "...", "playlist_url": "..."}: create a user."""
    if request.method == "GET":
        qs = User.objects.select_related("profile").order_by("id")
        return JsonResponse({"users": [_profile_json(u) for u in qs]})
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Body must be JSON"}, status=400)
    name, track_ids = body.get("name"), body.get("track_ids")
    if playlist_url := body.get("playlist_url"):
        playlist = MockPlaylist.objects.filter(url=playlist_url).first()
        if playlist is None:
            return JsonResponse({"error": f"No mock playlist for {playlist_url}"}, status=404)
        track_ids = track_ids_from_payload(playlist.payload)
    if not name or not isinstance(track_ids, list):
        return JsonResponse({"error": "Need 'name' and either 'track_ids' or 'playlist_url'"}, status=400)
    user = matching.create_user(name, [str(t) for t in track_ids])
    return JsonResponse(_profile_json(user), status=201)


@csrf_exempt
def user_detail(request, user_id):
    """GET: profile. PUT {"track_ids": [...]}: replace songs and recompute."""
    user = get_object_or_404(User.objects.select_related("profile"), pk=user_id)
    if request.method == "PUT":
        try:
            track_ids = json.loads(request.body or b"{}").get("track_ids")
        except json.JSONDecodeError:
            track_ids = None
        if not isinstance(track_ids, list):
            return JsonResponse({"error": "Need a 'track_ids' list"}, status=400)
        matching.set_user_tracks(user, [str(t) for t in track_ids])
        user.refresh_from_db()
    elif request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    return JsonResponse(_profile_json(user))


@require_GET
def user_matches(request, user_id):
    """GET ?k=5: nearest users by audio-feature profile."""
    user = get_object_or_404(User.objects.select_related("profile"), pk=user_id)
    k = min(int(request.GET.get("k", 5)), 100)
    return JsonResponse({"user_id": user.pk, "matches": matching.nearest_neighbors(user, k)})


@require_GET
def playlists(request):
    """GET: all mock playlists (url, name, song count). ?url=...: one full payload."""
    if url := request.GET.get("url"):
        playlist = get_object_or_404(MockPlaylist, url=url)
        return JsonResponse({"url": playlist.url, "payload": playlist.payload})
    return JsonResponse({"playlists": [
        {"url": p.url, "name": p.payload["name"], "track_count": len(p.payload["items"])}
        for p in MockPlaylist.objects.order_by("url")
    ]})


def index(request):
    return render(request, "tracks/index.html", {"appsync": chat_feed.browser_config()})


MATCHES_SHOWN = 4
# The made-up listeners (Riley and friends) stay out of matching unless
# SPOTAFRIEND_FAKE_USERS=on, so only people who really imported a playlist match.
FAKE_USERS = os.environ.get("SPOTAFRIEND_FAKE_USERS", "off").lower() == "on"
SAMPLE_SONGS = 5


@csrf_exempt
@require_POST
def import_playlist(request):
    """The demo flow in one call. POST {"playlist_url": "...", "name": "..."}
    -> the playlist's tracks, the user's profile, and their nearest users."""
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Body must be JSON"}, status=400)
    url = normalize_playlist_url(body.get("playlist_url") or "")
    if url is None:
        return JsonResponse({"error": "That doesn't look like a Spotify playlist link"}, status=400)
    try:
        payload = fetch_playlist(url)
    except PlaylistNotFound:
        return JsonResponse({"error": "We couldn't find that playlist"}, status=404)

    name = (body.get("name") or "").strip() or "You"
    user, _ = User.objects.update_or_create(playlist_url=url, defaults={"name": name})
    track_ids = track_ids_from_payload(payload)
    matching.set_user_tracks(user, track_ids)
    user.refresh_from_db()

    genres = {}
    for tid, genre in Track.objects.filter(track_id__in=track_ids).values_list("track_id", "track_genre"):
        genres.setdefault(tid, []).append(genre)
    tracks = [
        {
            "id": t["id"],
            "name": t["name"],
            "artists": [a["name"] for a in t["artists"]],
            "album": t["album"]["name"],
            "genres": sorted(genres.get(t["id"], [])),
            "analyzed": t["id"] in genres,
        }
        for t in (it["track"] for it in payload["items"] if it.get("track") and it["track"].get("id"))
    ]
    my_artists = {a for t in tracks for a in t["artists"]}

    if FAKE_USERS:
        seed.retune_demo_friend(track_ids, seed_key=url)
    matches = matching.nearest_neighbors(
        user, MATCHES_SHOWN, pin_demo_friend=FAKE_USERS, include_bots=FAKE_USERS)
    if matches:
        top = User.objects.get(pk=matches[0]["user_id"])
        # With live chat on, the page announces matches over AppSync instead,
        # so both people (on any computer) hear about it the same way.
        if not chat_feed.available():
            notifications.notify_match(user, top, matches[0]["score"])
        if top.is_bot:
            chat.queue_greeting(bot=top, human=user)
    for m in matches:
        their_ids = UserTrack.objects.filter(user_id=m["user_id"]).values_list("track_id", flat=True)
        their_songs = {}
        for row in Track.objects.filter(track_id__in=list(their_ids)).order_by("-popularity").values(
            "track_id", "track_name", "artists"
        ):
            their_songs.setdefault(row["track_id"], row)
        m["shared_artists"] = sorted(my_artists & {a for s in their_songs.values() for a in s["artists"].split(";")})
        m["shared_tracks"] = sorted(their_songs[tid]["track_name"] for tid in set(track_ids) & set(their_songs))
        m["top_songs"] = [
            {"name": s["track_name"], "artists": s["artists"].split(";")}
            for s in list(their_songs.values())[:SAMPLE_SONGS]
        ]

    return JsonResponse({
        "user": _profile_json(user),
        "playlist": {"url": url, "name": payload.get("name", "Your playlist")},
        "tracks": tracks,
        "matches": matches,
    })


def _read_json(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return None


def _conversation_json(conversation):
    return {
        "id": conversation.pk,
        "messages": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "body": m.body,
                "song": {"id": m.song_id, "name": m.song_name, "artists": m.song_artists} if m.song_id else None,
                "created_at": m.created_at.isoformat(),
            }
            for m in chat.visible_messages(conversation)
        ],
        "typing": chat.bot_is_typing(conversation),
        "status": chat.effective_status(conversation),
        "requested_by": conversation.requested_by_id,
    }


@csrf_exempt
@require_POST
def start_conversation(request):
    """POST {"user_id": me, "other_user_id": them}: ask to chat, or reopen an
    existing chat. The other person has to accept before messages go through."""
    body = _read_json(request) or {}
    user = get_object_or_404(User, pk=body.get("user_id"))
    other = get_object_or_404(User, pk=body.get("other_user_id"))
    if user.pk == other.pk:
        return JsonResponse({"error": "You can't chat with yourself"}, status=400)
    conversation = chat.request_chat(user, other)
    return JsonResponse({**_conversation_json(conversation), "other": {"id": other.pk, "name": other.name}})


@csrf_exempt
@require_POST
def respond_to_chat(request, conversation_id):
    """POST {"user_id": me, "accept": true|false}: answer a chat request."""
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    body = _read_json(request) or {}
    user = get_object_or_404(User, pk=body.get("user_id"))
    try:
        chat.respond(conversation, user, accept=bool(body.get("accept")))
    except chat.ChatError as e:
        return JsonResponse({"error": str(e)}, status=400)
    other = chat.other_participant(conversation, user)
    return JsonResponse({**_conversation_json(conversation), "other": {"id": other.pk, "name": other.name}})


@csrf_exempt
def conversation_messages(request, conversation_id):
    """GET ?viewer=<user id>: all messages so far, and the viewer's notices
    for this chat count as read. POST {"sender_id", "body"} sends a message;
    {"sender_id", "track_id"} shares a song from the sender's list."""
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    viewer_id = request.GET.get("viewer")
    if request.method == "POST":
        body = _read_json(request) or {}
        text = (body.get("body") or "").strip()
        sender_id = body.get("sender_id")
        if sender_id not in (conversation.user_a_id, conversation.user_b_id):
            return JsonResponse({"error": "Sender isn't part of this chat"}, status=403)
        sender = User.objects.get(pk=sender_id)
        if not chat.can_message(conversation):
            return JsonResponse({"error": _not_accepted_reason(conversation, sender)}, status=403)
        song = None
        if track_id := body.get("track_id"):
            song = chat.find_song(sender, str(track_id))
            if song is None:
                return JsonResponse({"error": "That song isn't in your playlist"}, status=400)
        elif not text:
            return JsonResponse({"error": "Message is empty"}, status=400)
        if len(text) > chat.MAX_MESSAGE_LENGTH:
            return JsonResponse({"error": f"Messages are limited to {chat.MAX_MESSAGE_LENGTH} characters"}, status=400)
        chat.send_message(conversation, sender, text, song=song)
        viewer_id = sender_id
    elif request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    if str(viewer_id) in (str(conversation.user_a_id), str(conversation.user_b_id)):
        notifications.mark_conversation_read(User(pk=int(viewer_id)), conversation)
        notifications.touch_last_seen(viewer_id)
    return JsonResponse(_conversation_json(conversation))


def _not_accepted_reason(conversation, sender):
    other = chat.other_participant(conversation, sender)
    if chat.effective_status(conversation) == Conversation.DECLINED:
        return "This chat request was declined"
    if conversation.requested_by_id == sender.pk:
        return f"{other.name} hasn't accepted your chat request yet"
    return f"Accept {other.name}'s chat request first"


NOTIFICATIONS_SHOWN = 20


@csrf_exempt
def user_notifications(request, user_id):
    """GET: latest notifications and unread count. POST: mark all read."""
    user = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        notifications.mark_all_read(user)
    elif request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    notifications.touch_last_seen(user.pk)  # the page checks in here every few seconds
    items = notifications.visible(user).select_related("from_user", "conversation")[:NOTIFICATIONS_SHOWN]
    return JsonResponse({
        "unread": notifications.visible(user).filter(read=False).count(),
        "notifications": [
            {
                "id": n.id,
                "kind": n.kind,
                "text": n.text,
                "from_user": {"id": n.from_user.pk, "name": n.from_user.name} if n.from_user else None,
                "conversation_id": n.conversation_id,
                "created_at": n.created_at.isoformat(),
                "read": n.read,
                # A chat request that's still waiting for this user's answer.
                "needs_answer": (
                    n.kind == Notification.CHAT_REQUEST
                    and chat.effective_status(n.conversation) == Conversation.PENDING
                    and n.conversation.requested_by_id == n.from_user_id
                ),
            }
            for n in items
        ],
    })


@csrf_exempt
def user_email_alerts(request, user_id):
    """GET: whether email alerts are available and this user's status.
    POST {"email": "..."}: sign up; AWS sends a confirmation email first."""
    user = get_object_or_404(User, pk=user_id)
    if not email_alerts.available():
        return JsonResponse({"available": False})
    try:
        if request.method == "POST":
            email = ((_read_json(request) or {}).get("email") or "").strip()
            state = email_alerts.subscribe(email)
            user.email = email
            user.save(update_fields=["email"])
        elif request.method == "GET":
            state = email_alerts.status(user.email)
        else:
            return JsonResponse({"error": "Method not allowed"}, status=405)
    except email_alerts.EmailAlertError as e:
        return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"available": True, "email": user.email, "status": state})


def chat_page(request):
    return render(request, "tracks/chat.html", {"appsync": chat_feed.browser_config()})
