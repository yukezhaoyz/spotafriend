---
name: public-url
description: Give the local Spotafriend server a public https:// URL through a free Cloudflare quick tunnel, downloading cloudflared first if it's missing, and show a QR code for it in chat so people can scan it. Use when the user wants to share the demo, open it on another device or phone, get a public or https link, or start/restart the Cloudflare tunnel.
---

# Public URL for the demo (Cloudflare quick tunnel)

The app runs on one laptop (`manage.py runserver`, port 8000). A Cloudflare
quick tunnel gives it a public `https://<random-words>.trycloudflare.com`
address with no Cloudflare account. Both demo devices then open that URL and
share the one server.

HTTPS matters: the page needs a secure context for `crypto.randomUUID()` and
for the location used by the distance slider, so a plain `http://` LAN
address doesn't work from another device.

## Steps

1. **Make sure the server is running** on port 8000. If it isn't, start it in
   a terminal tab (from `backend/`):

   ```bash
   ../.venv/bin/python manage.py runserver 8000
   ```

2. **Check and install** (downloads `cloudflared` into `~/.local/bin` if it
   isn't on the PATH there already, then checks the server answers):

   ```bash
   .claude/skills/public-url/start-tunnel.sh --check
   ```

   Homebrew isn't used, because `brew install` can fail on machines whose
   `/usr/local` folders belong to another user.

   For the QR code, the project's `.venv` needs `segno` (a small pure-Python
   QR library). If `.venv/bin/python -c "import segno"` fails, install it:

   ```bash
   .venv/bin/pip install segno
   ```

3. **Start the tunnel in its own terminal tab** so it keeps running and the
   user can stop it with Ctrl-C:

   ```bash
   .claude/skills/public-url/start-tunnel.sh
   ```

   If running it yourself is blocked (it opens the laptop to the internet,
   so permission checks may refuse it), give the user that command to run
   in a terminal tab instead.

4. **Read the URL** from the tab: the script prints a `Public URL:` banner
   once `cloudflared` reports it, followed by a QR code drawn in the terminal
   and a `Saved: <path>.png` line. Give the user that URL.

5. **Show the QR code in chat** so people can scan it with their phones.
   Use the PNG from the `Saved:` line, or make one (it also prints the path):

   ```bash
   .venv/bin/python .claude/skills/public-url/make_qr.py https://<the-url>
   ```

   Then send that PNG to the user as an image they can see in the
   conversation (for example with a send-file tool set to render it inline).
   If there's no way to show images, point them at the QR code in the
   tunnel's terminal tab instead.

6. **Check it** after a minute (a new quick tunnel answers with HTTP 530 at
   first while its address spreads):

   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" https://<the-url>/
   ```

   Expect `200`.

## Things to tell the user

- The laptop, the server tab and the tunnel tab all have to stay running for
  the whole demo; closing either tab takes the site down.
- Every new tunnel gets a **new random URL** (and so a new QR code), so share
  it again after a restart.
- Restarting the server clears everyone's setup (everything is in memory), so
  people set up again.
- The page sends the AppSync API key to every visitor, which is fine for a
  short demo; issue a new key afterwards if the URL was shared widely.
- `PORT=8001 .claude/skills/public-url/start-tunnel.sh` tunnels a different port.
