"""Fake listeners and mock playlists for the demo."""
import math
import random
import string

from collections import Counter

from .matching import MATCH_FEATURES, create_user, feature_stats, set_user_tracks
from .models import MockPlaylist, Track, User

SONGS_PER_USER = 30

FAKE_USERS = [
    ("Maya", ["indie", "indie-pop"]),
    ("Theo", ["indie-pop", "folk"]),
    ("Jordan", ["hip-hop", "dancehall"]),
    ("Priya", ["hip-hop", "r-n-b"]),
    ("Leo", ["edm", "house"]),
    ("Sam", ["techno", "edm"]),
    ("Clara", ["classical", "piano"]),
    ("Felix", ["ambient", "classical"]),
    ("Rosa", ["reggaeton", "latino"]),
    ("Diego", ["salsa", "latin"]),
    ("Hana", ["k-pop", "j-pop"]),
    ("Kai", ["pop", "dance"]),
    ("Nora", ["acoustic", "singer-songwriter"]),
    ("Eli", ["metal", "hard-rock"]),
    ("Zoe", ["punk", "rock"]),
    ("Omar", ["jazz", "blues"]),
    ("Ava", ["country", "folk"]),
    ("Ravi", ["pop", "hip-hop", "edm"]),
]


def seed_fake_users(seed=42):
    rng = random.Random(seed)
    for name, genres in FAKE_USERS:
        pool = sorted(set(
            Track.objects.filter(track_genre__in=genres, popularity__gte=40).values_list("track_id", flat=True)
        ))
        create_user(name, rng.sample(pool, min(SONGS_PER_USER, len(pool))), is_bot=True)

    # Starts with a generic pop playlist; retune_demo_friend reshapes it per import.
    pool = sorted(set(Track.objects.filter(track_genre="pop", popularity__gte=40).values_list("track_id", flat=True)))
    create_user(DEMO_FRIEND_NAME, rng.sample(pool, SONGS_PER_USER), is_demo_friend=True, is_bot=True)


DEMO_FRIEND_NAME = "Riley"
# Share of the importer's analyzed songs the demo friend also "has". The rest
# are popular songs from the importer's top genres, chosen so the friend's
# average lands right next to the importer's.
DEMO_FRIEND_OVERLAP = 0.6
# Target profile distance from the importer, varied per playlist so the
# score reads 98-99% rather than one telltale number every time.
DEMO_FRIEND_DISTANCE = (0.10, 0.16)


def retune_demo_friend(track_ids, seed_key):
    """Rebuild the demo friend's songs to resemble this playlist, so they
    match genuinely: high score, real shared songs, artists and reasons.
    seed_key (the playlist URL) makes it repeatable for rehearsals."""
    friend = User.objects.filter(is_demo_friend=True).first()
    rows = list(Track.objects.filter(track_id__in=track_ids).values_list("track_id", "track_genre"))
    if friend is None or not rows:
        return
    rng = random.Random(seed_key)
    analyzed = sorted({tid for tid, _ in rows})
    songs = {r["track_id"]: r for r in Track.objects.filter(track_id__in=analyzed).values("track_id", *MATCH_FEATURES)}
    target = {f: sum(r[f] for r in songs.values()) / len(songs) for f in MATCH_FEATURES}
    stats = feature_stats()

    def scaled(row):
        return [row[f] / stats[f][1] for f in MATCH_FEATURES]

    goal = [target[f] / stats[f][1] for f in MATCH_FEATURES]
    goal_distance = rng.uniform(*DEMO_FRIEND_DISTANCE)
    shared = rng.sample(analyzed, max(1, round(len(analyzed) * DEMO_FRIEND_OVERLAP)))

    top_genres = [g for g, _ in Counter(g for _, g in rows).most_common(3)]
    candidates = {
        r["track_id"]: scaled(r)
        for r in Track.objects.filter(track_genre__in=top_genres, popularity__gte=40)
        .exclude(track_id__in=analyzed)
        .values("track_id", *MATCH_FEATURES)
    }

    # Greedily add whichever song brings the friend's running average closest
    # to goal_distance from the playlist's average. Aiming for exactly
    # zero would score a suspicious 100%.
    total = [sum(col) for col in zip(*(scaled(songs[tid]) for tid in shared))]
    extra = []
    for _ in range(len(analyzed) - len(shared)):
        n = len(shared) + len(extra) + 1
        best = min(
            (tid for tid in sorted(candidates) if tid not in extra),
            key=lambda tid: abs(
                math.dist([(t + c) / n for t, c in zip(total, candidates[tid])], goal) - goal_distance
            ),
            default=None,
        )
        if best is None:
            break
        extra.append(best)
        total = [t + c for t, c in zip(total, candidates[best])]
    friend_tracks = shared + extra
    rng.shuffle(friend_tracks)
    set_user_tracks(friend, friend_tracks)


# (playlist name, genres to sample from). Popular songs only, so they look
# familiar on stage.
MOCK_PLAYLISTS = [
    ("Late Night Indie", ["indie", "indie-pop", "alt-rock"]),
    ("Gym Hype", ["hip-hop", "edm", "dance"]),
    ("Sunday Morning Coffee", ["acoustic", "jazz", "singer-songwriter"]),
    ("Fiesta Latina", ["reggaeton", "latino", "salsa"]),
    ("K-Pop Stan", ["k-pop"]),
    ("Study Focus", ["classical", "piano", "ambient"]),
    ("Headbanger", ["metal", "hard-rock", "punk"]),
    ("Road Trip Country", ["country", "folk"]),
]

# Songs that aren't in the dataset, mixed into one playlist so the demo can
# show partial coverage ("27 of 29 songs analyzed").
UNKNOWN_TRACKS = [
    {"id": "0unknownTrack00000000a", "name": "Brand New Single", "artists": [{"name": "Upcoming Artist"}], "album": {"name": "Brand New Single"}},
    {"id": "0unknownTrack00000000b", "name": "Basement Demo", "artists": [{"name": "Local Band"}], "album": {"name": "Demos"}},
]


def _fake_playlist_id(rng):
    return "".join(rng.choices(string.ascii_letters + string.digits, k=22))


def seed_mock_playlists(seed=7):
    rng = random.Random(seed)
    for i, (name, genres) in enumerate(MOCK_PLAYLISTS):
        rows = Track.objects.filter(track_genre__in=genres, popularity__gte=50).values(
            "track_id", "track_name", "artists", "album_name"
        )
        by_id = {r["track_id"]: r for r in rows}  # dedupe across genres
        picked = rng.sample(sorted(by_id), min(rng.randint(20, 30), len(by_id)))
        tracks = [
            {
                "id": by_id[tid]["track_id"],
                "name": by_id[tid]["track_name"],
                "artists": [{"name": a} for a in by_id[tid]["artists"].split(";")],
                "album": {"name": by_id[tid]["album_name"]},
            }
            for tid in picked
        ]
        if i == 0:
            tracks += UNKNOWN_TRACKS
        url = f"https://open.spotify.com/playlist/{_fake_playlist_id(rng)}"
        MockPlaylist.objects.create(url=url, payload={"name": name, "items": [{"track": t} for t in tracks]})

