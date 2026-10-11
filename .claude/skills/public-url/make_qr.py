"""Make a scannable QR code for the demo's public URL.

    make_qr.py URL [PNG_PATH]

Prints the QR code in the terminal and saves it as a PNG (default: the
system temp folder, spotafriend-public-url-qr.png), then prints the PNG's path.
Needs segno: .venv/bin/pip install segno
"""
import sys
import tempfile
from pathlib import Path

try:
    import segno
except ImportError:
    sys.exit("segno isn't installed. From the project folder: .venv/bin/pip install segno")


def main():
    if len(sys.argv) < 2 or not sys.argv[1].startswith("https://"):
        sys.exit(__doc__)
    url = sys.argv[1]
    png = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(tempfile.gettempdir()) / "spotafriend-public-url-qr.png"

    qr = segno.make(url, error="m")
    qr.terminal(compact=True)
    # Black on white with a wide quiet zone scans best, even off a screen.
    qr.save(png, scale=12, border=4, dark="#000000", light="#ffffff")
    print(f"QR code for {url}")
    print(f"Saved: {png}")


if __name__ == "__main__":
    main()
