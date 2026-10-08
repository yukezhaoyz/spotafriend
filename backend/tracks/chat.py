"""One-to-one chat. The page checks for new messages every couple of
seconds; made-up listeners answer on their own after a short pause."""
import random
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from . import notifications
from .models import Conversation, Message, MockPlaylist, Notification, Track, UserTrack

BOT_REPLY_DELAY = (1.5, 3.0)  # seconds
MAX_MESSAGE_LENGTH = 1000

BOT_FOLLOW_UPS = [
    "Okay we clearly need to swap playlists 😄",
    "What have you had on repeat this week?",
    "Ever been to a concert that changed your taste?",
    "If you could only keep one album forever, which one?",
    "Honestly I'd go to a show with you. Who's on your list?",
    "Haha same. Got any underrated songs I should hear?",
]


def get_or_create_conversation(user, other):
    a, b = sorted([user, other], key=lambda u: u.pk)
    conversation, _ = Conversation.objects.get_or_create(user_a=a, user_b=b)
    return conversation


def other_participant(conversation, user):
    return conversation.user_b if conversation.user_a_id == user.pk else conversation.user_a


def visible_messages(conversation):
    return conversation.messages.filter(created_at__lte=timezone.now())


def bot_is_typing(conversation):
    return conversation.messages.filter(created_at__gt=timezone.now()).exists()


def find_song(user, track_id):
    """{id, name, artists} for a song in the user's own list, else None.
    Details come from the dataset, or from the user's playlist for songs
    the dataset doesn't have."""
    if not UserTrack.objects.filter(user=user, track_id=track_id).exists():
        return None
    row = Track.objects.filter(track_id=track_id).values("track_name", "artists").first()
    if row:
        return {"id": track_id, "name": row["track_name"], "artists": row["artists"].split(";")}
    playlist = MockPlaylist.objects.filter(url=user.playlist_url).first() if user.playlist_url else None
    for item in (playlist.payload["items"] if playlist else []):
        track = item.get("track") or {}
        if track.get("id") == track_id:
            return {"id": track_id, "name": track["name"], "artists": [a["name"] for a in track["artists"]]}
    return None


@transaction.atomic
def send_message(conversation, sender, body, song=None):
    other = other_participant(conversation, sender)
    if song:
        artists = ", ".join(song["artists"])
        body = body or f"🎵 {song['name']} — {artists}"
        if other.is_bot:
            # A shared song always gets its own reaction, so whatever the bot
            # was still "typing" goes out first.
            _deliver_pending_now(conversation)
    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        body=body,
        song_id=song["id"] if song else None,
        song_name=song["name"] if song else None,
        song_artists=", ".join(song["artists"]) if song else None,
        created_at=timezone.now(),
    )
    notifications.notify_message(message, recipient=other)
    # Quick back-to-back texts share one pending reply.
    if other.is_bot and not bot_is_typing(conversation):
        _queue_bot_reply(conversation, bot=other, human=sender, trigger=message)
    return message


def _deliver_pending_now(conversation):
    now = timezone.now()
    pending = conversation.messages.filter(created_at__gt=now)
    Notification.objects.filter(conversation=conversation, created_at__gt=now).update(created_at=now)
    pending.update(created_at=now)


GREETING_DELAY = 6  # seconds after import


@transaction.atomic
def queue_greeting(bot, human):
    """Have a made-up match say hi first, shortly after the human imports a
    playlist. Skipped if the two have already talked."""
    conversation = get_or_create_conversation(human, bot)
    if conversation.messages.exists():
        return
    _queue_bot_reply(conversation, bot=bot, human=human, delay=GREETING_DELAY)


def _queue_bot_reply(conversation, bot, human, delay=None, trigger=None):
    replies_so_far = conversation.messages.filter(sender=bot).count()
    if trigger is not None and trigger.song_id:
        text = _song_reaction(bot, trigger)
    elif replies_so_far == 0:
        text = _opening_line(bot, human)
    else:
        text = BOT_FOLLOW_UPS[(replies_so_far - 1) % len(BOT_FOLLOW_UPS)]
    if delay is None:
        delay = random.uniform(*BOT_REPLY_DELAY)
    message = Message.objects.create(
        conversation=conversation, sender=bot, body=text, created_at=timezone.now() + timedelta(seconds=delay)
    )
    notifications.notify_message(message, recipient=human)


def _song_reaction(bot, message):
    if UserTrack.objects.filter(user=bot, track_id=message.song_id).exists():
        return f"No way, {message.song_name} is on my playlist too! 🙌"
    first_artist = message.song_artists.split(", ")[0]
    return f"Ooh, {message.song_name} by {first_artist}! Adding it to my queue 🎧"


def _artists_of(user):
    track_ids = UserTrack.objects.filter(user=user).values_list("track_id", flat=True)
    return {a for artists in Track.objects.filter(track_id__in=list(track_ids)).values_list("artists", flat=True)
            for a in artists.split(";")}


def _opening_line(bot, human):
    shared = sorted(_artists_of(bot) & _artists_of(human))
    if shared:
        return f"Hey {human.name}! I saw you listen to {shared[0]} too, what's your favorite song of theirs?"
    return f"Hey {human.name}! Our playlists are super similar. What are you listening to lately?"
