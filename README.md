# 🎧 Spotafriend

**Find your people through the music you love.**

Spotafriend takes the songs from a playlist, analyzes how they sound, builds a "taste profile," and matches the listener with like-minded people nearby. When two people match, both are notified instantly, and they can open a live chat and recommend songs to each other.

> **Scope:** A hackathon demo. The server runs on one laptop and keeps everything in an in-memory SQLite database that's rebuilt from the dataset each time it starts; no login, nothing saved. Live matching and chat go through **Amazon Web Services (AWS) AppSync**, and a free **Cloudflare tunnel** gives the laptop a public `https://` uniform resource locator (URL) so phones and other laptops can join.
>
> 📚 More in [`docs/`](docs/): [how we built it](docs/build-story.md) (what we tried and why we switched) and the [live demo script](docs/hackathon-demo-script.md).

---

## 🚀 Running Locally

**You need:** Python 3.9+ and git.

```bash
# 1. Get the code
git clone https://github.com/yukezhaoyz/spotafriend.git
cd spotafriend

# 2. Create a virtual environment and install the packages
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt

# 3. Download the dataset CSV and save it as dataset.csv in this folder
#    https://www.kaggle.com/datasets/maharshipandya/-spotify-tracks-dataset

# 4. (Optional) settings: copy the example and edit it, see "Configuration"
cp .env.example .env

# 5. Start the server
cd backend
../.venv/bin/python manage.py runserver
```

Then open **http://localhost:8000**. Startup takes a few seconds while it loads ~114,000 songs.

> Everything (users, chats, notifications) lives in memory and **resets when the server restarts**. The made-up listeners and demo playlists are recreated each time.

### Sharing it with a public URL

To open the demo on other devices, give the running server a public `https://` address with a free Cloudflare quick tunnel (no account needed). From the project folder, while the server runs:

```bash
.claude/skills/public-url/start-tunnel.sh
```

It downloads `cloudflared` into `~/.local/bin` if needed, then prints a `Public URL: https://….trycloudflare.com` banner and a Quick Response (QR) code people can scan with their phones (the QR code needs `segno`: `.venv/bin/pip install segno`; it's also saved as a Portable Network Graphics (PNG)). Keep it running during the demo; each start gets a new URL. It has to be `https://` because the page needs a secure context (for `crypto.randomUUID()` and the location used by the distance slider). In Claude Code, the `public-url` skill does the same thing.

### Hosting it permanently (Hugging Face Space)

For a link that keeps working without the laptop (for example a QR code at the end of a video), the app can run on a free **Hugging Face Docker Space**, at a permanent `https://<owner>-<space>.hf.space` address. Everything needed is in [`deploy/huggingface/`](deploy/huggingface/):

1. Create a free account at huggingface.co, then **New Space** → SDK **Docker** → template **Blank**, visibility **Public**.
2. In the Space's **Files** tab, upload `deploy/huggingface/Dockerfile` and `deploy/huggingface/README.md` (replacing the README it made).
3. In the Space's **Settings → Variables and secrets**, add these **secrets**: `SPOTAFRIEND_APPSYNC_HTTP_DOMAIN`, `SPOTAFRIEND_APPSYNC_REALTIME_DOMAIN`, `SPOTAFRIEND_APPSYNC_API_KEY` (the same three lines as in `.env`), and `SPOTAFRIEND_SECRET_KEY` (any long random text).
4. The Space builds by itself (a few minutes): it clones this repository's `main` branch and downloads the song dataset from its official Hugging Face mirror (BSD license), so `dataset.csv` is never uploaded. To pick up later changes on `main`, use **Settings → Factory rebuild**.

It runs as one always-on container. A free Space sleeps after about two days without visitors; the next visit wakes it in about a minute. As with the laptop, a restart clears everyone's setup.

---

## 🎬 Demo Walkthrough

The demo uses two devices on the same public URL (see "Sharing it with a public URL" above) and needs the AppSync settings in `.env` (see "Configuration").

1. **Person A** (laptop): type a name, click the **Late Night Indie** demo playlist, set the distance slider (for example **Within 5 miles**), and click **Find my people**. The page lists the songs (ones missing from the dataset are greyed out) and says no one else is here yet. Allow location when the browser asks.
2. **Person B** (phone): do the same with **Road Trip Country**.
3. Both screens show **"You've received a match!"** at once. Person B's match card shows the score and why: **85% · both into vocal tracks · both into mellow songs**, with no songs in common. Everyone else with the site open sees "A and B just matched!".
4. Both tap **Open chat**: a chat window titled with the other person's name. Messages arrive instantly.
5. Tap **+** in the chat, search a song or artist, and send it: it arrives as a **"Recommended a song"** card.

**Rehearsing alone:** set `SPOTAFRIEND_FAKE_USERS=on` to bring back the 18 made-up listeners and **Riley**, a demo friend who always matches you at ~98–99% by mirroring your playlist. Riley sends a chat request a few seconds after you import (click **Accept**), and replies to messages and songs you share with **🎵**. **Message** on another match sends a chat request that made-up listeners accept after ~2 seconds.

**Demo playlist links** (the same every time the server starts):

| Playlist | Link |
|---|---|
| Late Night Indie (includes 2 songs not in the dataset) | https://open.spotify.com/playlist/J6NKdKdnIizHJIQgJlgSIM |
| Gym Hype | https://open.spotify.com/playlist/5A7eIWYvvEXefqReTtJQBS |
| Sunday Morning Coffee | https://open.spotify.com/playlist/AIR9QxofjOaZlrjHLth16O |
| Fiesta Latina | https://open.spotify.com/playlist/ajgwb2Mjpvwh09CDfgvqZk |
| K-Pop Stan | https://open.spotify.com/playlist/NMWVmoyXmET9WDmLvYSv8e |
| Study Focus | https://open.spotify.com/playlist/Ufj9bKCOLKD6jHbXTgUi9m |
| Headbanger | https://open.spotify.com/playlist/WLWjiMhdQGDW2dlcgCb3du |
| Road Trip Country | https://open.spotify.com/playlist/PAnshW6NwpiCUf2kPnR9zA |

These are **made-up playlists stored in the app**, not real Spotify playlists; real Spotify import isn't built yet (see Task List).

---

## 💡 The Idea

1. **Import** – Paste a Spotify playlist link; we get its songs.
2. **Analyze** – We look up each song's audio features in a local dataset and build a taste profile.
3. **Match** – We compare that profile against other listeners nearby; when two people match, both are notified instantly, with the reasons why.
4. **Chat** – One tap opens a live chat with your match, and songs make the icebreaker: recommend one from the catalog.

---

## ✨ What's Built

- **Playlist import** from a link (share links, `spotify:playlist:` links or bare identifiers (IDs)), using the built-in demo playlists, with coverage ("27 songs · 25 analyzed").
- **Taste profile & matching** on the sound of your songs, with plain-English reasons ("both into mellow songs") and the songs and artists you share.
- **Distance slider** from "Within 1 mile" to "Across the world", using the browser's location rounded to about half a mile.
- **Instant match notifications across devices** ("You've received a match!") through AWS AppSync, plus "A and B just matched!" announcements for everyone else.
- **Live chat** between two people over an AppSync WebSocket, with **song recommendations** from the whole catalog (the **+** button). Nothing is stored.
- **Public URL with a QR code** through a free Cloudflare tunnel (one script, also a Claude Code skill).
- **In-app chat** (the original version): chat requests with Accept / Decline, song sharing from your playlist, a notification bell and pop-ups.
- **18 made-up listeners + Riley** for rehearsing alone; off by default (`SPOTAFRIEND_FAKE_USERS=on`).
- **Email alerts (optional)** through AWS Simple Notification Service (SNS) for people who are away from the site.
- **Structured Query Language (SQL) access** to the data for exploring it (read-only).

---

## ⚙️ Configuration

Settings live in a **`.env` file** in the project folder. Copy the example to start:

```bash
cp .env.example .env
```

`.env` is **gitignored**, so the values stay on your computer and never reach GitHub. `.env.example` *is* committed, so it only ever holds placeholders. All settings are optional; with no `.env`, the demo runs with email alerts off.

| Setting | What it does | Default |
|---|---|---|
| `SPOTAFRIEND_EMAIL_ALERTS` | Email alerts: `off`, `log` (print instead of sending) or `sns` (send via AWS) | `off` |
| `SPOTAFRIEND_SNS_TOPIC_ARN` | The SNS topic to send through, for example one a teammate created | empty (use `SPOTAFRIEND_SNS_TOPIC`) |
| `SPOTAFRIEND_SNS_TOPIC` | Topic name to look up or create in your own AWS account | `spotafriend-alerts` |
| `SPOTAFRIEND_APPSYNC_HTTP_DOMAIN`, `SPOTAFRIEND_APPSYNC_REALTIME_DOMAIN`, `SPOTAFRIEND_APPSYNC_API_KEY` | The AppSync Event application programming interface (API) that live chat runs on (see "Live chat" below). Off while empty | empty |
| `SPOTAFRIEND_FAKE_USERS` | `on` brings back Riley and the 18 made-up listeners (for rehearsing alone) | `off` |
| `SPOTAFRIEND_DEBUG` | `off` for a hosted copy: plain error pages instead of Django's debug pages | `on` |
| `SPOTAFRIEND_SECRET_KEY` | Django's secret key; set your own for a hosted copy | a development-only key |
| `SPOTAFRIEND_ALLOWED_HOSTS` | Extra hostnames the site may be served on, comma-separated (the Space uses `.hf.space`) | empty (only `localhost`) |
| `AWS_REGION` | AWS region | from the topic Amazon Resource Name (ARN), then `~/.aws/config` |
| `SPOTAFRIEND_AWAY_SECONDS` | Seconds without activity before someone counts as away | `60` |
| `SPOTAFRIEND_SITE_URL` | Link put in alert emails | `http://localhost:8000` |

**AWS login keys never go in `.env` or the code.** Set them up with `aws configure`, which stores them in `~/.aws/credentials`, outside the project. Your AWS user needs SNS permission to create topics, subscribe, list subscriptions and publish.

A setting typed in the terminal wins over `.env`, which is handy for one-off runs:

```bash
SPOTAFRIEND_EMAIL_ALERTS=log ../.venv/bin/python manage.py runserver
```

**How live chat works:** it runs on an [AWS AppSync Events](https://docs.aws.amazon.com/appsync/latest/eventapi/event-api-welcome.html) API. Create one once (it reuses the API if it exists and makes a new API key each run), then paste the three lines it prints into `.env`:

```bash
../.venv/bin/python manage.py appsync_setup
```

Each computer runs its own server, so people on different computers are matched over AppSync: importing a playlist publishes `ARRIVED` to the `/chat/matches` channel, every page whose person has already imported answers with a `MATCH` naming a new room for the two of them, and both pages show "You've received a match!" with an **Open chat** button. The chat page is titled with the other person's name. The slider next to **Find my people** sets how far away a match may be, from "Within 1 mile" to "Across the world" (the default): two people match only when they're within both of their distances. Distance uses the browser's location, which the page asks for when you click **Find my people** and rounds to about half a mile before sharing it; without a location, only "Across the world" matches. Every new pair is also announced on the `/chat/announcements` channel, so everyone else with the site open gets "*Ana* and *Ben* just matched!". The first person to import hears from no one, so they get no notification until someone else arrives, and both pages need to be open. While live chat is on, the app's own "You matched with…" notification is skipped so matches only arrive this way. The made-up listeners (Riley and friends) are off unless `SPOTAFRIEND_FAKE_USERS=on`.

Clicking **Start chat** on a match opens `/chat/` in a new tab and publishes a `CHAT_REQUEST` with a new room id to the `/chat/requests` channel. Every other open page shows "*name* wants to chat with you" with an **Open chat** button that joins the same room. Both chat pages hold a WebSocket to AppSync, subscribe to `/chat/rooms/<room id>` and publish messages to it, so messages arrive instantly. The **+** button next to the message box searches the song catalog by title or artist; picking a song sends it to the other person as a "Recommended a song" card. Nothing is stored: when someone opens the chat, the page already there sends them the messages they missed, and the chat is gone once both pages close. Requests go to everyone with the site open, not only the person named. To chat across two computers, give both the same three settings. The API key is sent to the browser, so anyone who can open the site can use it; that's fine for a local demo and not beyond. Creating the API needs `appsync:CreateApi`, `appsync:ListApis`, `appsync:CreateChannelNamespace`, `appsync:ListChannelNamespaces` and `appsync:CreateApiKey`; chatting needs no AWS login at all.

**How email alerts work:** a user enters their email in the bell panel, AWS sends them a one-time confirmation link, and from then on messages and chat requests that arrive while they're away are emailed to them. Each user's subscription is filtered so they only get their own alerts.

---

## ⚠️ Spotify API Constraints

Real Spotify import isn't built yet. When it is, these apply:

| Constraint | What we do |
|---|---|
| `GET /audio-features` and related endpoints are **deprecated** and return `403` for apps created after Nov 27, 2024 (the [reference page](https://developer.spotify.com/documentation/web-api/reference/get-several-audio-features) is still up but marked *Deprecated*) | Use a public dataset for audio features (see below). |
| Since the Feb 2026 changes, Development Mode apps only get playlist items for playlists the **token's user owns or collaborates on**. A plain client-credentials token (no user) won't return playlist songs. | Generate a token **once** for the app owner's account and store its refresh token in `.env`. Demo playlists must be owned by that account (create a playlist and add songs, or duplicate a public one). |
| The playlist tracks endpoint was renamed to `GET /playlists/{id}/items`, and the response field `tracks` is now `items` | Use the new endpoint and field names. |
| Development Mode requires the app owner to have **Spotify Premium** | Make sure whoever owns the developer app has Premium. |

**Fallback:** if Spotify is unreachable, the import falls back to the built-in demo playlists (`fetch_playlist` in `backend/tracks/playlists.py` is the one place to plug Spotify in).

---

## 📊 Song Features: Spotify Tracks Dataset

Since Spotify's audio features API is deprecated, we use the **[Spotify Tracks Dataset by maharshipandya](https://www.kaggle.com/datasets/maharshipandya/-spotify-tracks-dataset)** on Kaggle (also mirrored on [Hugging Face](https://huggingface.co/datasets/maharshipandya/spotify-tracks-dataset) if you don't want to log in to Kaggle).

It contains **~114,000 tracks across ~114 genres**, collected from the Spotify API before the deprecation. Each row includes:

- `track_id` – the Spotify track ID (joins directly with tracks from a playlist)
- `artists`, `track_name`, `album_name`, `popularity`, `track_genre`
- Audio features: `danceability`, `energy`, `valence`, `tempo`, `acousticness`, `instrumentalness`, `speechiness`, `liveness`, `loudness`, `key`, `mode`

**How we use it:**
1. The server loads `dataset.csv` into an in-memory SQLite table (`tracks`) every time it starts.
2. When a playlist is imported, each song is looked up by `track_id`.
3. The same song can appear once per genre, so profiles average over **distinct** songs (duplicates have identical features).
4. Songs not in the dataset still show in the playlist; they just don't add audio features.

**Known limitation:** 114,000 tracks is a small slice of Spotify's catalog, and the dataset isn't updated. Popular songs will mostly match; niche and recent releases often won't. We show **match coverage** (for example "27 songs · 25 analyzed"). For the demo, build playlists mostly from well-known songs.

> A cleaned version (one row per song, all of its genres, plus a genre group) is on the `data-cleaning` branch as `data/songs_clean.csv`. It isn't merged or used by the server yet.

**Exploring the data with SQL** (read-only; tables: `tracks`, `users`, `user_tracks`, `user_profiles`, `mock_playlists`, `conversations`, `messages`, `notifications`):

```bash
cd backend
../.venv/bin/python manage.py sql "SELECT track_genre, COUNT(*) FROM tracks GROUP BY track_genre LIMIT 5"
../.venv/bin/python manage.py sql      # interactive prompt; end statements with ;
```

---

## 🏗️ Architecture

```
 Phone / laptop browsers                     Laptop
┌──────────────────────────┐   HTTPS   ┌───────────────────┐   ┌──────────────────────────┐
│ index.html + chat.html   │◀─────────▶│ Cloudflare tunnel │──▶│ Django 4.2 :8000         │
│ plain JavaScript         │           │ (cloudflared)     │   │ matching · chat · bell   │
└────────────┬─────────────┘           └───────────────────┘   │ in-memory SQLite:        │
             │ WebSocket (publish/subscribe)                   │ 114k tracks + users      │
             ▼                                                 └────────────┬─────────────┘
┌──────────────────────────────────────────┐                                │ optional
│ AWS AppSync Events (namespace "chat")    │                   ┌────────────▼─────────────┐
│ /matches  /announcements  /requests      │                   │ AWS SNS: email alerts    │
│ /rooms/<room id>                          │                   │ when you're away         │
└──────────────────────────────────────────┘                   └──────────────────────────┘
```

- **Backend:** Django 4.2, Python
- **Database:** SQLite in memory (rebuilt from `dataset.csv` on each start)
- **Frontend:** two HyperText Markup Language (HTML) pages with plain JavaScript, no build step (`index.html`, `chat.html`)
- **Real-time:** AWS AppSync Events; each page keeps one WebSocket to AWS for matches, announcements and chat. The browser talks to AWS directly; the server only hands out the endpoint and key.
- **In-app chat and the bell:** the page checks the server for news every 1.5–2 seconds
- **Public URL:** Cloudflare quick tunnel (`cloudflared`), QR code via `segno`
- **Email:** AWS SNS via `boto3` (optional)

The server handles one request at a time on purpose: the shared in-memory database fails with "database table is locked" when two requests write at once, and requests take only milliseconds.

---

## 🧮 Matching Approach

**What's built (version 1):** each user's profile is the average of six audio features over their distinct songs: `danceability`, `energy`, `valence`, `acousticness`, `instrumentalness`, `speechiness`. (Tempo is stored and shown, but left out of matching.)

Each feature is put on a common scale by dividing by its spread across the dataset (z-scores), so no single feature dominates. Users are compared by distance:

```
distance² = Σ over features ((yours − theirs) / spread_of_feature)²
score     = 100 × 2^(−distance²)        # 100 = identical, 50 at distance 1.0
```

Nearest neighbours come from a single SQL query over `user_profiles`. That's plenty fast for thousands of users. **Reasons** list features where both people lean the same way compared with the average song ("both into upbeat songs").

**Planned (version 2), from the original plan:** add genres, artists and shared songs to the score, for example:

```
score = 0.35 * sound + 0.25 * cosine(genres) + 0.25 * weightedJaccard(artists) + 0.15 * jaccard(tracks)
```

Shared artists and songs are already calculated and shown on match cards; they just don't affect the score yet.

---

## 🔌 API

All endpoints are under `http://localhost:8000/api/`. No login; users are identified by id.

| Endpoint | What it does |
|---|---|
| `POST import/` `{playlist_url, name}` | The demo flow: playlist songs, your profile, your matches |
| `GET playlists/` · `GET playlists/?url=…` | List demo playlists · one playlist's songs |
| `GET users/` · `POST users/` | List users · create one from `track_ids` or `playlist_url` |
| `GET/PUT users/<id>/` | A user's profile · replace their songs |
| `GET users/<id>/matches/?k=5` | Nearest users with score and reasons |
| `GET/POST users/<id>/notifications/` | Notifications and unread count · mark all read |
| `GET/POST users/<id>/email-alerts/` | Email alert status · sign up with `{email}` |
| `POST conversations/` `{user_id, other_user_id}` | Send a chat request (or reopen a chat) |
| `POST conversations/<id>/respond/` `{user_id, accept}` | Accept or decline a chat request |
| `GET/POST conversations/<id>/messages/` | Read messages · send `{sender_id, body}` or share `{sender_id, track_id}` |
| `GET tracks/?genre=&artist=&q=` | Search songs |
| `GET schema/` · `POST query/` `{sql}` | Dataset columns · run read-only SQL |

---

## 📁 Project Structure

```
spotafriend/
├── dataset.csv                  # the song dataset (download; gitignored)
├── .env.example                 # settings template; copy to .env (gitignored)
├── README.md
├── docs/                        # build story, live demo script
├── deploy/huggingface/          # Dockerfile + README for a Hugging Face Space
├── .claude/skills/public-url/   # Claude Code skill + start-tunnel.sh for a public URL
└── backend/                     # Django project
    ├── manage.py
    ├── requirements.txt
    ├── config/                  # settings (incl. .env loading) and URLs
    └── tracks/                  # the app
        ├── models.py            # tables: tracks, users, profiles, chats, notifications…
        ├── loader.py            # loads dataset.csv into memory at startup
        ├── seed.py              # made-up listeners, Riley, demo playlists
        ├── playlists.py         # reading playlist links (Spotify plugs in here)
        ├── matching.py          # taste profiles and nearest neighbours
        ├── chat.py              # chat requests, messages, bot replies
        ├── notifications.py     # the bell and pop-ups
        ├── email_alerts.py      # AWS SNS email alerts
        ├── chat_feed.py         # live chat settings (AWS AppSync Events)
        ├── middleware.py        # one request at a time (see Architecture)
        ├── views.py, urls.py    # the API
        ├── templates/tracks/index.html   # the main web page
        ├── templates/tracks/chat.html    # the live chat page
        ├── templates/tracks/_appsync.html  # AppSync WebSocket client both pages use
        └── management/commands/   # `manage.py sql`, `manage.py appsync_setup`
```

---

## ✅ Task List

### 0. Setup
- [ ] Create a Spotify Developer app (owner account needs Premium)
- [ ] Add redirect uniform resource identifier (URI) `http://127.0.0.1:8888/callback` (only used by the one-time token script)
- [x] Backend (Django) and demo page
- [x] `.env.example` and `.env` loading
- [x] `.gitignore` (`.venv`, `.env`, `dataset.csv`)
- [x] Dataset as a comma-separated values (CSV) file, downloaded manually (see Running Locally)
- [x] One-command start (`manage.py runserver`)

### 1. Spotify Token (one-time)
- [ ] Script that opens the Spotify consent page once, catches the redirect, prints the refresh token to paste into `.env`
- [ ] Scopes: `playlist-read-private`, `playlist-read-collaborative`
- [ ] Server helper that swaps the refresh token for a fresh access token when needed

### 2. Dataset Import
- [x] Load the CSV into a `tracks` table (at startup, in memory)
- [x] Average over distinct songs (same `track_id` repeats per genre)
- [ ] Switch to the cleaned dataset from the `data-cleaning` branch (one row per song, all genres)
- [x] Index on `track_id`
- [ ] Lookup by normalized `track_name` + artist
- [x] Put features on a common scale (z-scores)

### 3. Playlist Import
- [x] `POST /api/import/` takes a playlist URL or ID and a display name
- [ ] Fetch `GET /playlists/{id}/items` from Spotify (handle pagination, skip null/local tracks)
- [x] Save the playlist songs for that user
- [x] Demo playlists stored in the app (currently the only source)
- [ ] Create demo playlists on the Spotify owner's account

### 4. Taste Profile
- [x] Look up each track in the dataset by `track_id`
- [ ] Fall back to name + artist
- [x] Sound profile
- [ ] Genre, artist and song sets in the score
- [x] Match coverage ("25 of 27 songs analyzed")
- [ ] Profile page: sound radar chart, top genres, top artists, coverage

### 5. Fake Users & Matching
- [x] 18 made-up listeners with genre-themed playlists, plus Riley the demo friend
- [x] Distance-based similarity with plain-English reasons
- [ ] Cosine / Jaccard / weighted Jaccard for genres, artists and songs
- [x] `GET /api/users/<id>/matches/` returns ranked matches with score and reasons
- [x] Match cards ("98% match — both into mellow songs, you both play …")

### 6. Chat & Notifications
- [ ] "Who am I?" user switcher (today, refreshing the page forgets who you are)
- [x] Chat requests with Accept / Decline
- [x] Messages; the page checks for new ones every 1.5 seconds
- [x] Instant delivery with WebSockets: live chat over AWS AppSync (the in-app chat still checks every 1.5 seconds)
- [x] Start a chat from a match card; history is kept while the server runs
- [x] Share songs from your playlist in chat
- [x] Made-up listeners accept requests and reply; first reply mentions a shared artist
- [x] Notification bell and pop-ups
- [x] Optional email alerts via AWS SNS

### 7. Live Features (AWS AppSync)
- [x] AppSync Event API, set up with `manage.py appsync_setup`
- [x] Match people across computers ("You've received a match!" on both)
- [x] Announce every match to everyone on the site
- [x] Live chat rooms; late joiners get missed messages; nothing stored
- [x] Song recommendations from the catalog in chat
- [x] Distance slider with rounded browser location
- [x] Made-up listeners off by default for the real demo

### 8. Demo Prep
- [x] Dark, Spotify-ish styling; loading and error states
- [x] Demo walkthrough (above)
- [x] Public URL and QR code (Cloudflare tunnel script and skill)
- [x] Live demo script and build story (`docs/`)
- [ ] Record a backup video

---

## 🔭 Out of Scope

- User login / accounts
- Hosting on a server (the demo runs on a laptop and is shared through a Cloudflare tunnel)
- Saving data across restarts
- Reading other people's private playlists
- Moderation, blocking, reporting
- Mobile app

---

## 👥 Team

- Shoghine Grigoryan
- Shuxin (Doris) Jin
- Thomas Katz
- Oluchi Calista Igwilo
- Xiaoying (Sarah) Chen
- Yuke Zhao
