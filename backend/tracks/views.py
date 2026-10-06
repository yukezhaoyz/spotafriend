import json
import sqlite3

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import matching, seed
from .playlists import PlaylistNotFound, fetch_playlist, normalize_playlist_url, track_ids_from_payload
from .loader import run_readonly_sql
from .models import MockPlaylist, Track, User, UserTrack

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
    return render(request, "tracks/index.html")


MATCHES_SHOWN = 4
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

    seed.retune_demo_friend(track_ids, seed_key=url)
    matches = matching.nearest_neighbors(user, MATCHES_SHOWN, pin_demo_friend=True)
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
