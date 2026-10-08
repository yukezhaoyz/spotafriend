"""User taste profiles and nearest-neighbour search.

A profile is the mean of each feature over the user's distinct dataset songs.
Users are compared on MATCH_FEATURES (everything but tempo) by Euclidean
distance after standardizing each feature by its spread across the dataset
(z-scores). Without that, widely spread features like acousticness would
outweigh narrow ones like speechiness. The mean cancels out in a z-score
difference:

    z_a - z_b = (a - mean)/std - (b - mean)/std = (a - b)/std

so the stored raw means are enough, and the distance needs only weights:

    d^2 = sum_f ((a_f - b_f) / std_f)^2

Nearest neighbours are found by a brute-force SQL scan over user_profiles.
That's one indexed row read per user and stays well under a millisecond per
thousand users, so no spatial index is needed at this scale.
"""
import math

from django.db import connection, transaction

from .models import Track, User, UserProfile, UserTrack

FEATURES = ["danceability", "energy", "valence", "acousticness", "instrumentalness", "speechiness", "tempo"]
# Features used to compare users. Tempo is kept in the profile for display
# but left out of matching.
MATCH_FEATURES = [f for f in FEATURES if f != "tempo"]

# Profile distance at which the score drops to 50%. Calibrated against the
# seeded users: related tastes sit at 0.3-0.8 apart, unrelated ones 1.5-4.4.
HALF_SCORE_DISTANCE = 1.0

# feature -> (mean, std) over distinct dataset songs; filled at startup.
_stats = {}


def compute_feature_stats():
    cols = ", ".join(f"AVG({f}), AVG({f} * {f})" for f in FEATURES)
    distinct = f"SELECT DISTINCT track_id, {', '.join(FEATURES)} FROM tracks"
    with connection.cursor() as cur:
        cur.execute(f"SELECT {cols} FROM ({distinct})")
        row = cur.fetchone()
    for i, f in enumerate(FEATURES):
        mean, mean_sq = row[2 * i], row[2 * i + 1]
        _stats[f] = (mean, math.sqrt(mean_sq - mean * mean))


def feature_stats():
    return dict(_stats)


@transaction.atomic
def set_user_tracks(user, track_ids):
    """Replace the user's songs and recompute their profile."""
    unique_ids = list(dict.fromkeys(track_ids))  # dedupe, keep order
    UserTrack.objects.filter(user=user).delete()
    UserTrack.objects.bulk_create(
        UserTrack(user=user, track_id=tid, position=i) for i, tid in enumerate(unique_ids)
    )
    return rebuild_profile(user, unique_ids)


def rebuild_profile(user, track_ids):
    songs = list(Track.objects.filter(track_id__in=track_ids).values("track_id", *FEATURES).distinct())
    means = {f: (sum(s[f] for s in songs) / len(songs) if songs else None) for f in FEATURES}
    profile, _ = UserProfile.objects.update_or_create(
        user=user,
        defaults={"track_count": len(track_ids), "matched_count": len(songs), **means},
    )
    return profile


def score_from_distance(distance):
    """Map distance to 0-100: 100 when identical, 50 at HALF_SCORE_DISTANCE."""
    return round(100 * 2 ** (-((distance / HALF_SCORE_DISTANCE) ** 2)), 1)


def nearest_neighbors(user, k=5, pin_demo_friend=False):
    """The k users whose profiles are closest to this user's, best first.
    With pin_demo_friend, the demo friend is listed first regardless."""
    weights = [1 / _stats[f][1] ** 2 for f in MATCH_FEATURES]
    d2 = " + ".join(f"%s * (p.{f} - me.{f}) * (p.{f} - me.{f})" for f in MATCH_FEATURES)
    sql = f"""
        SELECT p.user_id, u.name, {d2} AS d2
        FROM user_profiles p
        JOIN user_profiles me ON me.user_id = %s
        JOIN users u ON u.id = p.user_id
        WHERE p.user_id != me.user_id
          AND p.matched_count > 0 AND me.matched_count > 0
        ORDER BY {"u.is_demo_friend DESC," if pin_demo_friend else ""} d2
        LIMIT %s
    """
    with connection.cursor() as cur:
        cur.execute(sql, [*weights, user.pk, k])
        rows = cur.fetchall()

    me = user.profile
    others = UserProfile.objects.in_bulk([r[0] for r in rows])
    results = []
    for user_id, name, sq in rows:
        distance = math.sqrt(sq)
        results.append({
            "user_id": user_id,
            "name": name,
            "distance": round(distance, 4),
            "score": score_from_distance(distance),
            "reasons": shared_traits(me, others[user_id]),
        })
    return results


def z_scores(profile):
    return {f: (getattr(profile, f) - _stats[f][0]) / _stats[f][1] for f in MATCH_FEATURES}


# How to describe a user who leans (low, high) on each feature.
TRAIT_LABELS = {
    "danceability": ("laid-back grooves", "danceable tracks"),
    "energy": ("mellow songs", "high-energy songs"),
    "valence": ("moody songs", "upbeat songs"),
    "acousticness": ("electronic production", "acoustic sounds"),
    "instrumentalness": ("vocal tracks", "instrumentals"),
    "speechiness": ("melodic vocals", "lyric-heavy tracks"),
}
SIMILAR_LABELS = {
    "danceability": "danceability", "energy": "energy", "valence": "mood",
    "acousticness": "acoustic feel", "instrumentalness": "vocal mix", "speechiness": "vocal style",
}

# Profiles average 20-30 songs, which pulls them toward the dataset mean, so
# a quarter of a song-level standard deviation is already a clear lean.
LEAN_THRESHOLD = 0.25
MAX_REASONS = 3


def shared_traits(a, b):
    """Plain-English reasons two users matched, strongest first. Features
    where both lean the same way from the average song ("both into upbeat
    songs"); if there are none, the features where they're closest."""
    za, zb = z_scores(a), z_scores(b)
    shared = sorted(
        (
            (min(abs(za[f]), abs(zb[f])), f"both into {TRAIT_LABELS[f][za[f] > 0]}")
            for f in MATCH_FEATURES
            if abs(za[f]) >= LEAN_THRESHOLD and abs(zb[f]) >= LEAN_THRESHOLD and (za[f] > 0) == (zb[f] > 0)
        ),
        reverse=True,
    )
    if shared:
        return [text for _, text in shared[:MAX_REASONS]]
    closest = sorted(MATCH_FEATURES, key=lambda f: abs(za[f] - zb[f]))
    return [f"similar {SIMILAR_LABELS[f]}" for f in closest[:2]]


def create_user(name, track_ids, **fields):
    user = User.objects.create(name=name, **fields)
    set_user_tracks(user, track_ids)
    return user
