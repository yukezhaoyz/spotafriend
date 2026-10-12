# Spotafriend: 60-second demo video script

A narrated walkthrough for the Datathon Season 2026 demo video: sell the
problem, show the product as a user would, and make the value obvious.

- **No people on camera.** The characters are their screens: **Person A** is a laptop,
  **Person B** is a phone. Hands are fine; faces never appear.
- **Person A** sets up first with the **Late Night Indie** demo playlist.
- **Person B** sets up second with **Road Trip Country**. They match at **85%**
  ("both into vocal tracks", "both into mellow songs"), the highest-scoring pair of demo playlists.
- Both open the same public uniform resource locator (URL) (see "Sharing it with a public URL" in the README).
- Narration is about 155 words, read over quiet café jazz.

---

## 0:00–0:12 · The problem

| Time | Shot | How to make it |
|---|---|---|
| 0:00–0:04 | **Map animation:** thin lines arc from cities around the world (Seoul, Mumbai, São Paulo, Lagos, Shanghai) and all land on **Vancouver**, right as the narration says "Northeastern Vancouver". | Google Earth Studio (free), or a Keynote/PowerPoint slide with Magic Move, recorded as video. |
| 0:04–0:07 | **Vancouver, no faces:** the SkyTrain gliding past, the waterfront, the Northeastern Vancouver building. | Free stock footage from Pexels or Pixabay ("Vancouver SkyTrain", "Vancouver waterfront"), or film the building yourselves. |
| 0:07–0:12 | **The friend-app problem:** hands swiping through grey profile cards that are just a photo placeholder and a one-line bio ("hi! 23 · likes travel"). Cut between **night** (desk lamp, headphones: Person A) and **day** (car dashboard or café table, earbuds: Person B). | Mock the cards up in Figma, Canva or Keynote; don't use a real app's screens or logo. Film over the shoulder, showing only the phone and hands. |

Captions timed to the narration: **new city** · **new country** · **nobody we know**.

> "Many of us at Northeastern Vancouver moved across the world to study here — new city,
> new country, nobody we know. You're surrounded by people, but finding *your* people is
> hard. Friend apps match you on photos and bios — not on what actually makes you click."

## 0:12–0:15 · The idea

**On screen:** the grey profile cards fade out, and the Spotafriend home page fades in on
Person A's laptop (only the laptop and hands in shot).

> "We think what you listen to is a better place to start."

## 0:15–0:27 · Setup: taste profile and distance

**On screen:** type Person A's name, click **Late Night Indie**, drag the slider to
**Within 5 miles**, click **Find my people**. The playlist's songs appear.

> "Person A adds a playlist. Spotafriend reads how each song sounds — mood, energy, how
> acoustic it is — across 114,000 tracks, and builds a taste profile. The slider keeps
> matches nearby."

## 0:27–0:41 · The match and why

**On screen:** Person B sets up with **Road Trip Country**. "You've received a match!" appears
on both screens. Zoom in on Person B's card: **85% match · both into vocal tracks · both into
mellow songs**.

> "When Person B joins, they're both notified right away. The match card says why — both lean
> mellow and vocal — even though one listens to late-night indie and the other to road-trip country."

## 0:41–0:53 · Chat and song recommendations

**On screen:** both open the chat from the notification ("Chat with Person B" / "Chat with Person A").

- Person B: *"hey, saw we matched. your playlist is really good"*
- Person B taps **+**, types an artist, and sends a song.
- Person A: *"haven't heard this one before. any others like it?"*

> "They open a chat straight from the notification, and the plus button finds any song to
> recommend."

## 0:53–1:00 · Close

**On screen:** both chat windows side by side, then an end card with the logo, tagline and
Quick Response (QR) code.

> "An easier first conversation — starting from something you already share. That's Spotafriend."

**Timing:** about 155 words, so it's tight. If a run-through comes out over 60 seconds,
drop "new city, new country, nobody we know" and "across 114,000 tracks"; the captions and
the screen already show both.

---

## Recording checklist

- **Fresh server:** restart it just before recording (everything is in memory), start the
  tunnel (`.claude/skills/public-url/start-tunnel.sh`), and scan its QR code on the phone.
- **Set up Person A first.** Person B's match card then shows the 85% score and the reasons.
- **Allow location on both devices before rolling**, so no permission pop-up appears on camera.
- **Record each screen on its own**, then cut them so "You've received a match!" lands on
  both at the same moment.
- **Song to recommend:** something soft and vocal that fits both playlists.
- **Opening footage, no faces:** the map animation, stock clips of Vancouver (Pexels and
  Pixabay clips are free to use without credit; still keep a list of the ones you use), and
  hand-and-phone shots with your own mock-up of a friend app. Anyone on the team can be the hands.
- **Music:** a royalty-free café jazz or lo-fi track (YouTube Audio Library or Pixabay Music),
  kept well under the narration.
- **Record the narration last**, in your own voice, over the finished cut.
- **If you're over 60 seconds**, trim the Vancouver clips first; keep the match moment and
  the song recommendation.
