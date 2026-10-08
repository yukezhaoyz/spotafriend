import sqlite3

from django.core.management.base import BaseCommand

from tracks.loader import run_readonly_sql


class Command(BaseCommand):
    help = "Run a read-only SQL query against the in-memory tracks table, or start a REPL with no argument."

    def add_arguments(self, parser):
        parser.add_argument("query", nargs="?", help="SQL to run; omit for an interactive prompt")

    def handle(self, *args, query=None, **options):
        if query:
            self._run(query)
            return
        self.stdout.write("Table: tracks. End statements with ';'. Ctrl-D to quit.")
        buf = []
        while True:
            try:
                line = input("sql> " if not buf else "...> ")
            except EOFError:
                self.stdout.write("")
                return
            buf.append(line)
            if line.rstrip().endswith(";"):
                self._run("\n".join(buf))
                buf = []

    def _run(self, sql):
        try:
            columns, rows, _ = run_readonly_sql(sql)
        except sqlite3.Error as e:
            self.stderr.write(f"error: {e}")
            return
        if not columns:
            return
        cells = [[str(v) for v in r] for r in rows]
        widths = [min(max([len(c)] + [len(r[i]) for r in cells]), 40) for i, c in enumerate(columns)]
        fmt = " | ".join(f"{{:<{w}.{w}}}" for w in widths)
        self.stdout.write(fmt.format(*columns))
        self.stdout.write("-+-".join("-" * w for w in widths))
        for r in cells:
            self.stdout.write(fmt.format(*r))
        self.stdout.write(f"({len(rows)} rows)")
