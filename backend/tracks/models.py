from django.db import models


class Track(models.Model):
    """One row of dataset.csv. track_id is not unique: the same track can
    appear once per genre."""

    row_index = models.IntegerField()  # the unnamed first CSV column
    track_id = models.CharField(max_length=32, db_index=True)
    artists = models.TextField()
    album_name = models.TextField()
    track_name = models.TextField()
    popularity = models.IntegerField()
    duration_ms = models.IntegerField()
    explicit = models.BooleanField()
    danceability = models.FloatField()
    energy = models.FloatField()
    key = models.IntegerField()
    loudness = models.FloatField()
    mode = models.IntegerField()
    speechiness = models.FloatField()
    acousticness = models.FloatField()
    instrumentalness = models.FloatField()
    liveness = models.FloatField()
    valence = models.FloatField()
    tempo = models.FloatField()
    time_signature = models.IntegerField()
    track_genre = models.CharField(max_length=64, db_index=True)

    class Meta:
        db_table = "tracks"

    def __str__(self):
        return f"{self.track_name} — {self.artists}"


class User(models.Model):
    name = models.CharField(max_length=100)
    # Set for users created by importing a playlist; re-importing the same
    # playlist updates this user instead of creating a duplicate.
    playlist_url = models.CharField(max_length=200, null=True, unique=True)
    # The demo friend: re-tuned to resemble each imported playlist and pinned
    # to the top of import results (see seed.retune_demo_friend).
    is_demo_friend = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.name


class UserTrack(models.Model):
    """A song a user submitted. Plain track_id rather than a FK: submitted
    songs may be missing from the dataset, and dataset track_ids repeat."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_tracks")
    track_id = models.CharField(max_length=32, db_index=True)
    position = models.IntegerField()

    class Meta:
        db_table = "user_tracks"
        unique_together = [("user", "track_id")]


class UserProfile(models.Model):
    """Mean audio features over a user's distinct songs found in the dataset.
    Feature columns stay null when none of the user's songs matched."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name="profile")
    track_count = models.IntegerField()
    matched_count = models.IntegerField()
    danceability = models.FloatField(null=True)
    energy = models.FloatField(null=True)
    valence = models.FloatField(null=True)
    acousticness = models.FloatField(null=True)
    instrumentalness = models.FloatField(null=True)
    speechiness = models.FloatField(null=True)
    tempo = models.FloatField(null=True)

    class Meta:
        db_table = "user_profiles"


class MockPlaylist(models.Model):
    """Stand-in for a Spotify playlist fetch, keyed by playlist URL. payload
    mirrors a trimmed Spotify playlist response:
    {"name": ..., "items": [{"track": {"id", "name", "artists": [{"name"}], "album": {"name"}}}]}
    """

    url = models.CharField(max_length=200, primary_key=True)
    payload = models.JSONField()

    class Meta:
        db_table = "mock_playlists"
