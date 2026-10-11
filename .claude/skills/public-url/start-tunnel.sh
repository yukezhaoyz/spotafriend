#!/usr/bin/env bash
# Give the local Spotafriend server a public https:// URL with a Cloudflare
# quick tunnel (no Cloudflare account needed). Downloads cloudflared into
# ~/.local/bin first if it isn't installed.
#
#   start-tunnel.sh            check everything, then run the tunnel (Ctrl-C stops it)
#   start-tunnel.sh --check    only install cloudflared and check the server
#
# PORT (default 8000) is where `manage.py runserver` is listening. Once the URL
# is known it also shows a QR code for it (needs segno in the project's .venv).
set -euo pipefail

PORT="${PORT:-8000}"
INSTALL_DIR="$HOME/.local/bin"
RELEASES="https://github.com/cloudflare/cloudflared/releases/latest/download"
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$SKILL_DIR/../../../.venv/bin/python"

find_cloudflared() {
  if command -v cloudflared >/dev/null 2>&1; then
    command -v cloudflared
  elif [ -x "$INSTALL_DIR/cloudflared" ]; then
    echo "$INSTALL_DIR/cloudflared"
  fi
}

install_cloudflared() {
  local os arch
  case "$(uname -s)" in
    Darwin) os=darwin ;;
    Linux) os=linux ;;
    *) echo "Unsupported system $(uname -s): install cloudflared by hand from https://github.com/cloudflare/cloudflared/releases" >&2; exit 1 ;;
  esac
  case "$(uname -m)" in
    x86_64 | amd64) arch=amd64 ;;
    arm64 | aarch64) arch=arm64 ;;
    *) echo "Unsupported processor $(uname -m): install cloudflared by hand" >&2; exit 1 ;;
  esac
  mkdir -p "$INSTALL_DIR"
  echo "Downloading cloudflared ($os-$arch) into $INSTALL_DIR ..."
  if [ "$os" = darwin ]; then
    # macOS builds come as a .tgz holding the binary.
    curl -fsSL "$RELEASES/cloudflared-darwin-$arch.tgz" | tar -xz -C "$INSTALL_DIR"
  else
    curl -fsSL "$RELEASES/cloudflared-linux-$arch" -o "$INSTALL_DIR/cloudflared"
  fi
  chmod +x "$INSTALL_DIR/cloudflared"
}

CLOUDFLARED="$(find_cloudflared)"
if [ -z "$CLOUDFLARED" ]; then
  install_cloudflared
  CLOUDFLARED="$INSTALL_DIR/cloudflared"
fi
echo "Using $("$CLOUDFLARED" --version)"

if ! curl -fs -o /dev/null "http://localhost:$PORT/"; then
  echo "Nothing is answering on http://localhost:$PORT/." >&2
  echo "Start the server first, from backend/:  ../.venv/bin/python manage.py runserver $PORT" >&2
  exit 1
fi
echo "Server is up on port $PORT."

[ "${1:-}" = "--check" ] && exit 0

# --http-host-header: Django only accepts "localhost" (settings.ALLOWED_HOSTS),
# so requests reach it looking local. --no-autoupdate: with its output piped,
# cloudflared would otherwise update itself and restart, under a new URL.
# The public URL is printed once it's known.
"$CLOUDFLARED" tunnel --no-autoupdate --url "http://localhost:$PORT" --http-host-header localhost 2>&1 |
  while IFS= read -r line; do
    echo "$line"
    if [[ "$line" =~ (https://[a-z0-9-]+\.trycloudflare\.com) ]]; then
      echo
      echo "=================================================================="
      echo "  Public URL: ${BASH_REMATCH[1]}"
      echo "  (it can answer with error 530 for the first minute)"
      echo "=================================================================="
      echo
      if [ -x "$VENV_PYTHON" ] && "$VENV_PYTHON" -c "import segno" 2>/dev/null; then
        "$VENV_PYTHON" "$SKILL_DIR/make_qr.py" "${BASH_REMATCH[1]}" || true
      else
        echo "(For a QR code: .venv/bin/pip install segno, then restart this script.)"
      fi
      echo
    fi
  done
