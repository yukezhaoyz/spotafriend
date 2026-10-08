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
    # Made-up listeners: they reply to chat messages automatically.
    is_bot = models.BooleanField(default=False)
    # Opted in to email alerts (see email_alerts.py).
    email = models.CharField(max_length=254, null=True)
    # Last time this user's page checked in; used to tell if they're away.
    last_seen = models.DateTimeField(null=True)
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


class Conversation(models.Model):
    """A chat between two users, stored with the lower user id first. It
    starts as a request that the other person accepts or declines."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"

    user_a = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    user_b = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    status = models.CharField(
        max_length=10, default=PENDING,
        choices=[(PENDING, "Waiting for an answer"), (ACCEPTED, "Accepted"), (DECLINED, "Declined")],
    )
    # When the status took effect. Bots accept with a time a moment in the
    # future, and until then the request still counts as pending.
    status_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "conversations"
        unique_together = [("user_a", "user_b")]


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    body = models.TextField()
    # Set when the message shares a song from the sender's playlist.
    song_id = models.CharField(max_length=32, null=True)
    song_name = models.TextField(null=True)
    song_artists = models.TextField(null=True)  # comma-separated, for display
    # Bot replies are saved with a time a moment in the future and stay
    # hidden until then, which reads as "typing..." on the page.
    created_at = models.DateTimeField()

    class Meta:
        db_table = "messages"
        ordering = ["created_at", "id"]


class Notification(models.Model):
    MATCH = "match"
    MESSAGE = "message"
    CHAT_REQUEST = "chat_request"
    CHAT_ANSWER = "chat_answer"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=20, choices=[
        (MATCH, "New match"), (MESSAGE, "New message"),
        (CHAT_REQUEST, "Chat request"), (CHAT_ANSWER, "Answer to a chat request"),
    ])
    text = models.CharField(max_length=300)
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name="+")
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, null=True, related_name="+")
    # Matches the message's time, so a bot reply's notification stays hidden
    # until the reply itself shows up.
    created_at = models.DateTimeField()
    read = models.BooleanField(default=False)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at", "-id"]
