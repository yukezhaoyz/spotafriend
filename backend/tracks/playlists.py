"""Turning a pasted playlist link into its songs."""
import re

from .models import MockPlaylist

# Matches open.spotify.com/playlist/<id>?si=..., spotify:playlist:<id>, or a bare id.
_PLAYLIST_ID = re.compile(r"(?:playlist[/:])?([A-Za-z0-9]{22})(?:[/?#].*)?$")


class PlaylistNotFound(Exception):
    pass


def normalize_playlist_url(raw):
    """Canonical https://open.spotify.com/playlist/<id> URL, or None if the
    input doesn't look like a playlist link."""
    match = _PLAYLIST_ID.search(raw.strip())
    return f"https://open.spotify.com/playlist/{match.group(1)}" if match else None


def fetch_playlist(url):
    """Playlist payload for a canonical URL. Only mock playlists for now;
    the real Spotify fetch plugs in here and falls back to the mock."""
    playlist = MockPlaylist.objects.filter(url=url).first()
    if playlist is None:
        raise PlaylistNotFound(url)
    return playlist.payload


def track_ids_from_payload(payload):
    """Track IDs from a playlist payload, skipping null/local items."""
    return [it["track"]["id"] for it in payload.get("items", []) if it.get("track") and it["track"].get("id")]
