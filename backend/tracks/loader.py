"""Builds the in-memory database from dataset.csv."""
import csv
import sqlite3
import time

from django.apps import apps
from django.conf import settings
from django.db import connection

from . import matching, seed

# Holding one raw connection open keeps the shared in-memory DB alive even
# when Django closes or recycles its own per-thread connections.
_anchor = None

INT_FIELDS = {"popularity", "duration_ms", "key", "mode", "time_signature"}
FLOAT_FIELDS = {
    "danceability", "energy", "loudness", "speechiness", "acousticness",
    "instrumentalness", "liveness", "valence", "tempo",
}


def _convert(field, value):
    if field in INT_FIELDS:
        return int(value)
    if field in FLOAT_FIELDS:
        return float(value)
    if field == "explicit":
        return value == "True"
    return value


def load_dataset():
    global _anchor
    if _anchor is not None:
        return
    _anchor = sqlite3.connect(settings.IN_MEMORY_DB_URI, uri=True, check_same_thread=False)

    start = time.monotonic()
    with connection.schema_editor() as editor:
        for model in apps.get_app_config("tracks").get_models():
            editor.create_model(model)

    with open(settings.DATASET_CSV, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        csv_fields = ["row_index"] + header[1:]
        rows = [
            [int(r[0])] + [_convert(name, v) for name, v in zip(header[1:], r[1:])]
            for r in reader
        ]

    cols = ", ".join(f'"{c}"' for c in csv_fields)
    placeholders = ", ".join("?" for _ in csv_fields)
    _anchor.executemany(f"INSERT INTO tracks ({cols}) VALUES ({placeholders})", rows)
    _anchor.commit()

    matching.compute_feature_stats()
    seed.seed_fake_users()
    seed.seed_mock_playlists()
    print(f"[tracks] loaded {len(rows):,} rows and {len(seed.FAKE_USERS)} fake users, "
          f"{len(seed.MOCK_PLAYLISTS)} mock playlists "
          f"into in-memory SQLite in {time.monotonic() - start:.1f}s")


def run_readonly_sql(sql, params=(), max_rows=None):
    """Run one SQL statement on a query_only connection. Returns (columns, rows, truncated)."""
    conn = sqlite3.connect(settings.IN_MEMORY_DB_URI, uri=True)
    try:
        conn.execute("PRAGMA query_only = ON")
        cur = conn.execute(sql, params)
        columns = [d[0] for d in cur.description] if cur.description else []
        if max_rows is None:
            return columns, cur.fetchall(), False
        rows = cur.fetchmany(max_rows + 1)
        return columns, rows[:max_rows], len(rows) > max_rows
    finally:
        conn.close()
