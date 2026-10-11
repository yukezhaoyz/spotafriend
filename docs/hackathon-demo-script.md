# Spotafriend: hackathon main demo script

A **5-minute live demo** followed by Q&A. It tells the story, shows the product live on two
devices, then explains how each feature is built, which tools we used and why.

**Speakers.** The script is split into five speaking parts so the whole team can take a
turn. Fill in names:

| Part | Who | What they do |
|---|---|---|
| **S1** Problem | | Opens and sells the problem |
| **S2** Demo narrator | | Talks the audience through the live demo |
| **Driver A** | | Plays **Person A** on the laptop (on the projector) |
| **Driver B** | | Plays **Person B** on a phone (mirrored or held to a camera) |
| **S3** Data & matching | | Explains the dataset and the matching math |
| **S4** Real-time & AWS | | Explains AppSync, distance, chat and sharing |

**Demo pair.** Person A uses **Late Night Indie**, Person B uses **Road Trip Country**.
They match at **85%** with "both into vocal tracks" and "both into mellow songs", the
highest-scoring pair of demo playlists (checked with the app's own matching code).

---

## 0:00–0:35 · The problem (S1)

**On screen:** title slide: *Spotafriend — Find your people through the music you love.*

> "A lot of us at Northeastern Vancouver moved across the world to study here — new city,
> new country, nobody we know. You're surrounded by people, but making real friends takes
> time. And the apps meant to help match you on a photo and a two-line bio — which tells
> you almost nothing about whether you'll actually get along.
>
> We think what you listen to says a lot more. Your playlist is something you didn't write
> to impress anyone. So we built Spotafriend: add a playlist, and it finds people near you
> whose music *feels* like yours — then gives you an easy way to start talking."

## 0:35–2:20 · Live demo (S2 narrates, Drivers A and B click)

**1. Person A sets up (Driver A, laptop).** Type a name, click **Late Night Indie**, drag
the distance slider to **Within 5 miles**, click **Find my people**.

> S2: "Person A pastes in a playlist and sets how far away a match can be — from within a
> mile to anywhere in the world. Spotafriend looks up every song, shows how many it could
> analyze, and builds a taste profile. Nobody else is here yet, so for now it just waits."

*Point at the coverage line ("27 songs · 25 analyzed": two songs aren't in the dataset) and
"No one else is here yet."*

**2. Person B sets up (Driver B, phone).** Same steps with **Road Trip Country**.

> S2: "Person B joins on a different device with a country playlist…"

**3. The match.** "You've received a match!" pops up on **both** screens at once.

> S2: "…and both of them find out instantly. Indie on one side, country on the other — you'd
> never match them by genre. But look at why they matched."

*Driver B shows Person B's match card: **85% match · both into vocal tracks · both into
mellow songs**.*

> S2: "85% — and they don't share a single song or artist. What they share is how their music
> *sounds*: both lean vocal and mellow. And everyone else on the site just got a little notice
> too: a new match happened."

**4. Chat and a song recommendation.** Both tap **Open chat**. The windows read "Chat with
Person B" and "Chat with Person A". Driver B types *"hey, saw we matched — your playlist is
really good"*, taps **+**, searches an artist, and sends a song. The "Recommended a song"
card appears on Person A's screen.

> S2: "One tap opens a private chat with their name on it. And the plus button searches the
> whole song catalog, so the first message can just be a song. That's the whole loop: playlist,
> match, conversation — in under a minute."

## 2:20–3:15 · How it works: data and matching (S3)

**On screen:** the architecture diagram below, then the formula.

> S3: "Spotify used to give developers 'audio features' for every song — danceability,
> energy, mood — but shut that off for new apps in late 2024. So we use a public Kaggle
> dataset of about 114,000 Spotify tracks with those features, loaded into an in-memory
> SQLite database when the server starts.
>
> Your taste profile is the average of six features across your songs — things like energy,
> how happy a song sounds, and how acoustic it is. We scale each feature by its spread across
> the dataset so none dominates, and the score is simply distance: identical taste is 100%,
> one standard step apart is 50%. Finding your closest people is a single SQL query. The
> reasons come from features where you *both* sit on the same side of the average song —
> so you get 'both into mellow songs' instead of a number nobody understands."

## 3:15–4:35 · How it works: real-time, distance and sharing (S4)

> S4: "The real-time part runs on **AWS AppSync Events**: managed publish-subscribe over
> WebSockets. We first built it on **SNS and SQS**, but SQS is a work queue — we had to poll
> it every second and it only returns a random sample of messages, so it got slower as it
> filled up. AppSync *pushes* every message instantly and costs per message, so we switched.
>
> When you set up, your page announces 'I've arrived'. Every page already there checks the
> distance and, if you're in range, replies with a private chat room for the two of you.
> Both pages get the notification; everyone else gets the announcement.
>
> Location is only shared if you allow it, and it's rounded to about half a mile first. Two
> people match only if they're within *both* of their limits. Chat rooms are channels too,
> and nothing is stored — not in our database, not in AWS.
>
> And to put it on your phones for free, the laptop runs a **Cloudflare tunnel** that gives
> it a public HTTPS address — one script, which also prints the QR code you scanned."

## 4:35–5:00 · Why it matters and what's next (S1)

> S1: "So: no photos, no bios, no awkward first line — you start from something you already
> share. Next, we'd connect real Spotify accounts so anyone can import their own playlists,
> add genres and shared artists into the score, and keep matches between visits.
> Thanks — we'd love your questions."

---

## Architecture (for the S3/S4 slide)

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

---

## Feature reference: what, how, tools, why

Use this to prepare the S3/S4 parts and for Q&A.

| Feature | How it's built | Tools | Why this way |
|---|---|---|---|
| **Playlist import** | Accepts share links, `spotify:playlist:` links or bare IDs; reads the songs from the built-in demo playlists. Shows coverage ("27 songs · 25 analyzed"). | Django view, `playlists.py` (the single place real Spotify plugs in) | Spotify now only returns playlist songs to the token owner's playlists, so the demo uses stored playlists. |
| **Song data** | `dataset.csv` loaded into an in-memory SQLite `tracks` table at startup, indexed on `track_id`. Profiles average over *distinct* songs (the dataset repeats a song once per genre). | Kaggle "Spotify Tracks Dataset" (~114k tracks, ~114 genres), SQLite | Spotify's audio-features API is deprecated for new apps. In-memory SQLite is fast, needs no setup, and rebuilds itself on every start. |
| **Taste profile & score** | Average of 6 features, z-scaled by each feature's spread; `score = 100 × 2^(−distance²)`; nearest neighbours in one SQL query. | Python, SQL | Simple, explainable, and fast for thousands of users. |
| **Plain-English reasons** | Features where both people sit on the same side of the dataset average, strongest first ("both into mellow songs"). Match cards also list shared songs and artists. | `matching.shared_traits` | A reason people can read beats a bare number. |
| **Distance slider** | 1, 5, 10, 25, 50, 100, 500, 1,000 miles or "Across the world". Browser geolocation rounded to 2 decimal places (≈ half a mile), great-circle (haversine) distance, and both people's limits must hold. | Browser Geolocation API | Newcomers want people *nearby*; rounding keeps exact locations private. |
| **Live cross-device matching** | `ARRIVED` → existing pages reply `MATCH` with a new room id → both show "You've received a match!". Repeat meetings reuse the room instead of re-notifying. | AWS AppSync Events (`/chat/matches`) | Each laptop runs its own server, so matching across devices has to happen through a shared real-time channel. |
| **Match announcements** | The page that creates a pair's room publishes `MATCHED`; everyone else sees "A and B just matched!". | AppSync (`/chat/announcements`) | Makes the site feel alive. |
| **Live chat** | Each room is a channel; messages are pushed over the WebSocket; a late joiner says `HELLO` and gets up to 50 missed messages as `HISTORY`. Nothing is stored. | AppSync (`/chat/rooms/<id>`), hand-written WebSocket client (`_appsync.html`) | Instant delivery with no database and no polling. |
| **Song recommendations** | **+** in the chat searches the catalog by title or artist, de-duplicated, and sends a "Recommended a song" card. | `/api/tracks/` search | The music becomes the icebreaker. |
| **Original in-app chat** (also built) | Chat requests with Accept / Decline, song sharing from your own playlist, notification bell and pop-ups; the page checks for news every 1.5–2 s. Made-up listeners (incl. "Riley", tuned to mirror your playlist) can be turned on to rehearse alone. | Django models, polling | Our first version, still there; the made-up listeners are off for the real demo (`SPOTAFRIEND_FAKE_USERS`). |
| **Email alerts** (optional) | If your page hasn't checked in for 60 s, new messages and chat requests are emailed. One SNS topic; each subscription has a filter on a key derived from the email, so people only get their own. | AWS SNS, boto3 | Reaches people who've left the site, without running a mail server. |
| **Read-only SQL explorer** | `manage.py sql` and `POST /api/query/` run queries with `PRAGMA query_only`. | SQLite | Lets the team explore the data safely. |
| **Public URL + QR code** | `.claude/skills/public-url/start-tunnel.sh` downloads `cloudflared` if needed, opens a free quick tunnel, prints the URL and a QR code (also a Claude Code skill). | Cloudflare quick tunnel, segno | The page needs HTTPS (for `crypto.randomUUID()` and location). Free, no account, no server to manage. |
| **One-command AWS setup** | `manage.py appsync_setup` creates or reuses the Event API, the `chat` namespace and an API key, then prints the `.env` lines. | boto3 | Repeatable setup for any teammate. |
| **Team workflow** | Every change landed through a GitHub pull request with a written description and test notes. | GitHub, Claude Code | Reviewable history for a six-person team. |

---

## Things you need to know before the demo

**Must-do setup (start 30 minutes before):**
1. Pull `main` and start the server: `cd backend && ../.venv/bin/python manage.py runserver`.
2. Start the tunnel: `.claude/skills/public-url/start-tunnel.sh`. Wait for the first `200`
   (a new tunnel answers **530 for about a minute**). Open the URL on **both** demo devices.
3. On both devices, **allow location** once now so the permission pop-up doesn't interrupt the demo.
4. Do a full dry run, then **restart the server** (everything is in memory, so a restart is how
   you clear the rehearsal users) and reload both pages. Don't restart the tunnel: its URL
   would change and the QR code with it.
5. Keep the laptop awake and plugged in (`caffeinate -d` in a terminal stops it sleeping).

**Behaviours to plan around:**
- **Order matters.** Person A must be set up and on the main page *before* Person B sets up.
  The page that's already there is what answers.
- **Only Person B's card shows the 85% and the reasons.** Person A's card says "Matched just
  now". Zoom in on Person B's screen for that line.
- **The score needs both people on the same server**, which the tunnel gives you. If each
  device ran its own server, the notification would still arrive but without a score.
- **If you invite the audience to scan the QR code**, ask them to just watch, not set up.
  Anyone who sets up would match with the presenters and flood their screens with
  notifications. Watchers still see "A and B just matched!", which is a nice moment.
- **Venue Wi-Fi:** the tunnel and AppSync both need outbound internet. Have a phone hotspot
  ready.
- **The song to recommend:** pick it in advance (a soft, vocal track; try searching an artist
  from Person A's playlist) so the search lands first time.

**Be upfront about these if asked (better from you than from a judge):**
- **Real Spotify import isn't built.** The playlists are stored demo playlists. Spotify's
  audio-features API is closed to new apps and playlist access now needs the owner's login,
  so we planned around it; `playlists.py` is where it plugs in.
- **The dataset is a snapshot of ~114k songs**, so niche or new songs may not be analyzed.
  That's why coverage is shown.
- **The AppSync API key is visible in the page.** That's fine for a demo; we'd swap it for
  per-user sign-in (for example Amazon Cognito) in a real product, and we'll rotate the key
  after the event.
- **No accounts or saved data:** a server restart clears everything. That was a deliberate
  scope choice for the hackathon.

**Housekeeping before judges open the repo:**
- Merge the open demo-video-script PR so `docs/` is on `main`.
- Update the README: its architecture diagram doesn't show AppSync or the tunnel yet, the task
  list still has "Instant delivery with WebSockets" unchecked (live chat does this now), and
  "Deployment" is listed as out of scope even though the tunnel makes the site public.
- Record a backup video of the live demo (it's still unchecked in the task list) in case the
  Wi-Fi fails on the day.

---

## Likely questions and short answers

- **"Why not just use Spotify's data?"** Spotify closed the audio-features endpoint to new
  apps in November 2024, so we use a public dataset collected before that.
- **"Is 85% meaningful?"** It's a distance between two six-number taste profiles, scaled so
  identical taste is 100% and one standard step apart is 50%. The reasons show which parts
  drive it.
- **"Why AppSync and not your own WebSocket server?"** It's managed, scales without us running
  anything, costs per message, and works across devices on different networks. We moved to it
  from SNS + SQS after seeing polling slow down.
- **"What about privacy?"** No accounts, nothing stored, chats disappear when both pages close,
  and location is rounded to about half a mile before it's shared, and only if you allow it.
- **"How would this scale?"** The score is one SQL query over profiles; the next step would be
  a persistent database, real accounts, and AppSync auth per user instead of a shared key.
- **"What would you build next?"** Real Spotify import, genres and shared artists in the score,
  saved matches, and a profile page with a taste chart.
