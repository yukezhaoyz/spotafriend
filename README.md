# 🎧 Spotafriend

**Find your people through the music you love.**

Spotafriend pulls the songs from a Spotify playlist, analyzes them, builds a "taste profile," and matches the listener with like-minded people. Once matched, they can chat in real time.

> **Scope:** A hackathon demo that runs **entirely on one laptop**. No login, no deployment. One Spotify call to fetch songs; everything else is local SQLite queries.

---

## 💡 The Idea

1. **Import** – Paste a Spotify playlist link; we fetch its songs.
2. **Analyze** – We look up each song's audio features in a local dataset and build a taste profile.
3. **Match** – We compare that profile against other listeners and rank the most compatible.
4. **Chat** – Open a chat with a match, with shared artists and songs as icebreakers.

---

## 🧭 Demo Approach

To keep things simple:

- **No login.** The app uses our own Spotify developer credentials stored in a local `.env` file.
- **One Spotify call path.** The server fetches playlist tracks from Spotify. That's the only external call.
- **Everything else is local.** Audio features, profiles, matches, and chat all live in SQLite.
- **Fake listeners.** We seed 15–20 made-up users with playlists built from the dataset, so there's always someone to match with.
- **"Who am I?" dropdown** replaces auth. Pick a user in the top bar; open two browser tabs as two users to demo chat.

---

## ⚠️ Spotify API Constraints

| Constraint | What we do |
|---|---|
| `GET /audio-features` and related endpoints are **deprecated** and return `403` for apps created after Nov 27, 2024 (the [reference page](https://developer.spotify.com/documentation/web-api/reference/get-several-audio-features) is still up but marked *Deprecated*) | Use a public dataset for audio features (see below). |
| Since the Feb 2026 changes, Development Mode apps only get playlist items for playlists the **token's user owns or collaborates on**. A plain client-credentials token (no user) won't return playlist songs. | Generate a token **once** for the app owner's account and store its refresh token in `.env`. Demo playlists must be owned by that account (create a playlist and add songs, or duplicate a public one). |
| The playlist tracks endpoint was renamed to `GET /playlists/{id}/items`, and the response field `tracks` is now `items` | Use the new endpoint and field names. |
| Development Mode requires the app owner to have **Spotify Premium** | Make sure whoever owns the developer app has Premium. |

**Fallback:** if Spotify is unreachable during the demo, load a saved playlist from `data/mock_playlists/*.json` instead. Same code path from there on.

---

## 📊 Song Features: Spotify Tracks Dataset

Since Spotify's audio features API is deprecated, we use the **[Spotify Tracks Dataset by maharshipandya](https://www.kaggle.com/datasets/maharshipandya/-spotify-tracks-dataset)** on Kaggle (also mirrored on [Hugging Face](https://huggingface.co/datasets/maharshipandya/spotify-tracks-dataset) if you don't want to log in to Kaggle).

It contains **~114,000 tracks across ~114 genres**, collected from the Spotify API before the deprecation. Each row includes:

- `track_id` – the Spotify track ID (joins directly with tracks from a playlist)
- `artists`, `track_name`, `album_name`, `popularity`, `track_genre`
- Audio features: `danceability`, `energy`, `valence`, `tempo`, `acousticness`, `instrumentalness`, `speechiness`, `liveness`, `loudness`, `key`, `mode`

**How we use it:**
1. Import the CSV into SQLite once (`npm run db:import-dataset`).
2. When a playlist is imported, look up each `track_id` in the dataset.
3. If an ID isn't found, try normalized `track_name` + first artist.
4. Unmatched tracks still count toward artist overlap; they just don't add audio features.

**Known limitation:** 114k tracks is a small slice of Spotify's catalog, and the dataset isn't updated. Popular songs will mostly match; niche and recent releases often won't. We show **match coverage** (e.g. "62% of your tracks analyzed"). For the demo, build playlists mostly from well-known songs.

---

## 🏗️ Architecture (local)

```
┌──────────────┐   HTTP / WebSocket   ┌──────────────────┐   one call   ┌─────────────┐
│   Frontend   │ ◀──────────────────▶ │     Backend      │ ───────────▶ │ Spotify API │
│ React + Vite │                      │ Node + Express   │  (playlist   └─────────────┘
│ :5173        │                      │ + Socket.IO      │   items)
└──────────────┘                      │ :3001            │
                                      └────────┬─────────┘
                                               │ local queries
                                        ┌──────▼──────┐
                                        │   SQLite    │
                                        │ dataset +   │
                                        │ users, chat │
                                        └─────────────┘
```

**Suggested stack** (swap freely):
- **Frontend:** React + Vite + Tailwind
- **Backend:** Node.js + Express
- **Realtime chat:** Socket.IO
- **Database:** SQLite via better-sqlite3

---

## 🧮 Matching Approach (v1)

For each user, build a profile:
- `sound`: average audio-feature vector across matched tracks (danceability, energy, valence, acousticness, instrumentalness, speechiness, normalized tempo)
- `genres`: frequency vector of `track_genre`
- `artists`: set of artists (weighted by how often they appear)
- `tracks`: set of track IDs

Compatibility score (0–100):

```
score = 0.35 * cosine(soundVectors)
      + 0.25 * cosine(genreVectors)
      + 0.25 * weightedJaccard(artists)
      + 0.15 * jaccard(tracks)
```

Tune weights during testing. Show *why* people matched: similar sound (e.g. both high-energy, upbeat), shared genres, shared artists, shared songs.

---

## ✅ Task List

### 0. Setup
- [ ] Create a Spotify Developer app (owner account needs Premium)
- [ ] Add redirect URI `http://127.0.0.1:8888/callback` (only used by the one-time token script)
- [ ] Scaffold `/client` (React + Vite) and `/server` (Express)
- [ ] Add `.env.example` (`SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`)
- [ ] Add `.gitignore` (`node_modules`, `.env`, `*.db`, `data/*.csv`)
- [ ] Download the [Spotify Tracks Dataset](https://www.kaggle.com/datasets/maharshipandya/-spotify-tracks-dataset) CSV into `data/`
- [ ] One-command dev start (`npm run dev` with `concurrently`)

### 1. Spotify Token (one-time)
- [ ] `npm run spotify:token` script: opens the Spotify consent page once, catches the redirect, prints the refresh token to paste into `.env`
- [ ] Scopes: `playlist-read-private`, `playlist-read-collaborative`
- [ ] Server helper that swaps the refresh token for a fresh access token when needed

### 2. Dataset Import
- [ ] `db:import-dataset` script: load CSV into a `tracks_dataset` table
- [ ] Deduplicate (same `track_id` appears under multiple genres — one feature row, keep all genres)
- [ ] Index on `track_id` and on normalized `track_name` + artist
- [ ] Normalize tempo and loudness to 0–1

### 3. Playlist Import
- [ ] `POST /api/import` takes a playlist URL or ID and a display name
- [ ] Fetch `GET /playlists/{id}/items` (handle pagination, skip null/local tracks)
- [ ] Save the playlist tracks for that user in SQLite
- [ ] Fallback: load from `data/mock_playlists/*.json` if the Spotify call fails
- [ ] Create 2–3 demo playlists on the owner's account and save their JSON as mocks

### 4. Taste Profile
- [ ] Look up each track in the dataset (by `track_id`, then name + artist)
- [ ] Build sound vector, genre vector, artist and track sets
- [ ] Store match coverage %
- [ ] Profile page: sound radar chart, top genres, top artists, coverage

### 5. Fake Users & Matching
- [ ] Seed script: 15–20 fake users, each with a genre-themed playlist sampled from the dataset (indie, hip-hop, EDM, classical, mixes)
- [ ] Similarity functions (cosine, Jaccard, weighted Jaccard)
- [ ] `GET /api/matches?userId=` returns ranked matches with score and reasons
- [ ] Matches page with match cards ("87% match — you both love …")

### 6. Chat
- [ ] "Who am I?" user dropdown (stored in app state, no auth)
- [ ] Socket.IO rooms per conversation
- [ ] Messages table: `id`, `conversation_id`, `sender_id`, `body`, `created_at`
- [ ] Start a chat from a match card; load history; send/receive live
- [ ] Icebreaker suggestions from shared music
- [ ] *(Nice-to-have)* Canned bot replies from fake users

### 7. Demo Prep
- [ ] Dark, Spotify-ish styling; loading and error states
- [ ] Demo script: import playlist → profile → matches → chat (two tabs)
- [ ] Record a backup video

---

## 🚀 Running Locally

```bash
# 1. Install
git clone <repo-url> spotafriend
cd spotafriend
npm install

# 2. Configure env
cp .env.example .env
# fill in SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET

# 3. Get a refresh token (one time) and paste it into .env
npm run spotify:token

# 4. Download the dataset CSV and save as data/spotify_tracks.csv
#    https://www.kaggle.com/datasets/maharshipandya/-spotify-tracks-dataset

# 5. Set up DB, import dataset, seed fake users
npm run db:migrate
npm run db:import-dataset
npm run db:seed

# 6. Start client + server
npm run dev
```

Then open **http://127.0.0.1:5173**.

---

## 📁 Planned Structure

```
spotafriend/
├── client/              # React + Vite frontend
│   └── src/
│       ├── pages/       # Import, Profile, Matches, Chat
│       └── components/
├── data/
│   ├── spotify_tracks.csv   # dataset (gitignored)
│   └── mock_playlists/      # saved playlist JSON for offline fallback
├── scripts/
│   └── spotify-token.js     # one-time refresh token helper
├── server/              # Express + Socket.IO backend
│   └── src/
│       ├── spotify/     # token refresh, playlist fetch
│       ├── matching/    # profiles + similarity
│       ├── chat/        # socket handlers
│       └── db/          # schema, dataset import, seed
├── .env.example
└── README.md
```

---

## 🔭 Out of Scope

- User login / accounts
- Deployment
- Reading other people's private playlists
- Moderation, blocking, reporting
- Mobile app

---

## 👥 Team

| Name | Role |
|---|---|
| | |
| | |
