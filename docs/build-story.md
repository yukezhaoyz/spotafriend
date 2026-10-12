# How we built Spotafriend

The story of the build in order: what we tried, what broke, what we switched to and why.
Dates are from the git history (October 2026); pull request (PR) numbers link each step to its code.

---

## 1. The plan (October 4)

We started with a README describing a **Node + React** app. That version was never built:
the code went in as **Django with a single HyperText Markup Language (HTML) page of plain JavaScript** instead. What that
gave us:

- One language, Python, for both the server and the data work (loading the dataset, the
  matching math).
- One page with no build step, so anyone on the team could open a file and change it.

## 2. Spotify wouldn't give us the data (October 5, PR #1)

The idea depends on knowing how each song *sounds*. Spotify used to provide this as "audio
features", but:

- **The audio-features endpoint is deprecated** and returns `403` for apps created after
  November 27, 2024, which includes ours.
- **Since February 2026, development-mode apps only see playlists the token's owner owns or
  collaborates on**, and the app owner needs Spotify Premium.

**What we did instead:**
- Used the **Spotify Tracks Dataset on Kaggle**: about 114,000 tracks with the audio
  features, collected before the deprecation. The server loads it into an **in-memory
  SQLite** database on every start. That means no database to install, and fast lookups.
- Stored **demo playlists inside the app**, and kept one function (`fetch_playlist`) as the
  place real Spotify import will plug in later.
- Built the matching: average six audio features per person, scale each by its spread across
  the dataset, and score by distance, with **plain-English reasons** ("both into mellow songs").
- Added **18 made-up listeners and "Riley"**, a demo friend whose songs are rebuilt to
  resemble whatever playlist you import. That let one person demo and test alone.

**Known limit we accepted:** the dataset is a snapshot. Niche and new songs often aren't in
it, so the page shows coverage ("27 songs · 25 analyzed"). Doris also built a cleaned
version (one row per song, all its genres) on the `data-cleaning` branch, which isn't wired
in yet.

## 3. Chat, notifications and email (October 7, PRs #2–#3)

- **Chat requests with Accept / Decline**, song sharing from your playlist, a notification
  bell and pop-ups. The page asked the server for news every 1.5–2 seconds.
- **Email alerts through Amazon Web Services (AWS) Simple Notification Service (SNS)** for people who've left the site. One topic serves
  everyone; each subscription has a **filter** on a key derived from the email address, so
  people only get their own alerts.
- **Settings in `.env`** (gitignored), with `.env.example` committed. AWS keys never go in
  the file; they come from `aws configure`.

**Issue: "database table is locked".** The in-memory SQLite database is shared between the
server's threads, and two writes at once fail immediately instead of waiting. With every page
checking in every couple of seconds, that happened a lot. **Fix:** a small middleware that
handles one request at a time. Requests take milliseconds, so nobody notices the queueing.

## 4. First try at real-time over AWS: SNS → SQS (October 9, PRs #4–#7)

We wanted people to hear about matches as they happened, through AWS.

- **#4** added a form to post to the SNS topic, to prove publishing worked.
- **#5 (Doris)** announced each new match on the SNS topic, delivered to a **Simple Queue Service (SQS) queue** that
  every page polled once a second.
- **Issue:** SQS hides a message from other readers while one is reading it, and each page
  deleted its own announcements, so other pages could miss them. **#6 (Doris)** switched to
  reading only, never deleting or hiding, so every page saw every announcement. It also added
  the switch to turn the made-up listeners off.
- **#7 (Shoghine)** reworded the announcement to "You have a match with *name*!".

## 5. Why SQS didn't work for chat, and the switch to AppSync (October 10, PR #8)

Next we built **two-person chat on the same SNS → SQS setup**: messages published to the topic
and polled from a queue. It worked, but it was the wrong tool:

- **SQS is a work queue**, built to hand each message to *one* worker. We were using it as a
  broadcast.
- Since we never deleted anything, the queue kept growing for days. Each poll returns only a
  **random sample of at most 10 messages**, so the more messages there were, the longer a
  specific one took to show up. Chat would get slower over time.
- Every open page polled every second, whether or not anything had happened.

**We switched chat to AWS AppSync Events**, a managed publish/subscribe service over
WebSockets:
- It **pushes** each message to everyone subscribed to a channel, instantly. No polling.
- It's pay-per-message, with nothing for us to run.
- Each chat room is its own channel, `/chat/rooms/<id>`, and the browser talks to AWS directly.

Two design choices came with it:
- **Nothing is stored.** When someone joins a room late, their page says `HELLO`, and the page
  already there replies with the last 50 messages (`HISTORY`).
- **`manage.py appsync_setup`** creates the application programming interface (API), the `chat` namespace and an API key, and
  prints the `.env` lines, so any teammate can set it up the same way.

The SNS → SQS match feed and the SNS form were removed at the same time. SNS stays for email.

## 6. Matching people on *different* computers (October 10, PRs #10–#11)

**Issue:** everyone runs their own server, and each server keeps its users in memory. A server
literally can't see the person on the other laptop, so it can't match them.

- **First attempt (#10):** after an import, the server published the match to an AppSync
  channel, and both pages could open the same room from it.
- **Final design (#11):** the matching moved into the pages. When you set up, your page
  publishes `ARRIVED` on `/chat/matches`. Every page whose person has already set up replies
  with `MATCH` and a fresh room for the two of you, and both pages show "You've received a
  match!". The first person to arrive hears from no one, so gets nothing, which is exactly
  the demo flow we wanted.
- **The made-up listeners became opt-in**, so the demo only ever matches real people.

**A process hiccup:** one PR was merged into the previous PR's branch *after* that branch had
already gone into `main`, so its changes never reached `main`. We re-landed them as #10.
Lesson: merge stacked PRs in order, or target `main` directly.

## 7. Debugging the second laptop

A teammate's laptop got a **401** from AppSync, and later no notifications at all.

- We confirmed the key itself worked by publishing a test event with `curl`: a HyperText Transfer Protocol (HTTP) 200 "OK" response.
- We opened a **listener on the AppSync channels** to watch traffic live. Events from our
  laptop arrived, but nothing ever came from the other machine, so the problem was on that
  machine (its `.env` key, its code version, or a server not restarted).
- It also caught a stray reply from one of our own forgotten test tabs, which we closed.
- **Lesson:** watching the channel is the fastest way to tell "my code" from "their setup".

## 8. Features for the demo (October 10, PRs #12–#13)

- **Match announcements (#12):** the page that creates a pair's room also posts `MATCHED` to
  `/chat/announcements`, so everyone else sees "A and B just matched!".
- **Song recommendations (#13):** a **+** in the chat window. Our first version read your
  imported songs from the main page through browser storage. We decided recommendations should
  live entirely in the chat window, so it searches the **whole song catalog** by title or artist
  instead. Duplicate rows, one per genre in the dataset, are removed.
- **Distance slider (#13):** from 1 mile to "Across the world". It uses the browser's
  location, **rounded to about half a mile before it's shared**, and two people match only if
  they're within *both* of their limits. This needs HyperText Transfer Protocol Secure (HTTPS), which shaped the next step.

## 9. Getting a public URL (October 10, PRs #14–#15)

To demo on phones, the site needed a public address, and it had to be **HTTPS**: browsers
only allow `crypto.randomUUID()` (which the page uses as soon as it loads) and location on
secure pages.

What we looked at:

| Option | Why not |
|---|---|
| **Elastic Compute Cloud (EC2)** | Our course AWS user didn't have the EC2 permissions, and we'd have had to set up HTTPS ourselves. |
| **App Runner** | Closed to new customers since April 30, 2026. |
| **Lightsail containers** | A good fit (HTTPS built in), but about $10/month and still needed permissions. |
| **Lambda, Render's free tier** | Both spin down when idle, which would wipe our in-memory data mid-demo. |
| **Cloudflare quick tunnel** ✅ | Free, no account, HTTPS out of the box; the laptop keeps running the server. |

Issues along the way:
- **`brew install cloudflared` failed** because some `/usr/local` folders on the laptop
  belonged to another user. We download the binary straight from Cloudflare's releases instead.
- **Django rejected the tunnel's hostname**, since it only allows `localhost`. The tunnel passes
  `--http-host-header localhost`.
- **The uniform resource locator (URL) changes on every start.** We considered a fixed AWS redirect (a Lambda function
  URL or an Amazon Simple Storage Service (S3) redirect) and decided it wasn't worth it for a demo.
- **`cloudflared` turned on auto-update** when its output was piped, and an update would
  restart it under a new URL mid-demo. We pass `--no-autoupdate`.

We packaged it as **one script plus a Claude Code skill** (`.claude/skills/public-url/`). It
downloads `cloudflared` if needed, checks the server is up, starts the tunnel, and prints the
URL with a **Quick Response (QR) code** (made with the `segno` library) so the audience can scan it.

## 10. Demo prep (October 10–11)

- Picked the demo pair by running every pair of demo playlists through our own matching
  code. **Late Night Indie + Road Trip Country** score highest, at **85%**, with no songs in
  common: a good way to show we match on *sound*, not genre.
- Wrote the 60-second video script and the live demo script (`docs/`).

---

## What we'd tell another team

- **Check what the API will actually give you before designing around it.** Spotify's changes
  reshaped our whole data plan.
- **Match the AWS service to the job.** Queues are for work; publish/subscribe is for
  broadcasting. We lost time making SQS do something it isn't for.
- **HTTPS decides more than you'd think.** Browser features like location and secure random identifiers (IDs)
  only work on secure pages, which drove our hosting choice.
- **Small PRs with written descriptions** made it easy to see what changed and why, for a team
  of six working in parallel.
