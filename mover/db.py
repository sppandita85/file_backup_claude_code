import sqlite3
import sys
from pathlib import Path


def get_connection(db_path: str) -> sqlite3.Connection:
    path = Path(db_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS moves (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filename    TEXT    NOT NULL,
            source_path TEXT    NOT NULL,
            dest_path   TEXT    NOT NULL,
            file_size   INTEGER NOT NULL,
            file_type   TEXT    NOT NULL,
            moved_at    TEXT    NOT NULL,
            status      TEXT    NOT NULL CHECK(status IN ('ok','skipped','error')),
            error_msg   TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_moves_moved_at ON moves(moved_at);
        CREATE INDEX IF NOT EXISTS idx_moves_file_type ON moves(file_type);

        CREATE TABLE IF NOT EXISTS run_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at      TEXT    NOT NULL,
            finished_at     TEXT,
            files_moved     INTEGER DEFAULT 0,
            files_skipped   INTEGER DEFAULT 0,
            files_errored   INTEGER DEFAULT 0,
            bytes_moved     INTEGER DEFAULT 0
        );
    """)
    conn.commit()


def insert_move(conn, *, filename, source_path, dest_path,
                file_size, file_type, moved_at, status, error_msg=None):
    conn.execute(
        """INSERT INTO moves
           (filename, source_path, dest_path, file_size, file_type, moved_at, status, error_msg)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (filename, source_path, dest_path, file_size, file_type, moved_at, status, error_msg),
    )
    conn.commit()


def insert_run_start(conn, started_at: str) -> int:
    cur = conn.execute(
        "INSERT INTO run_log (started_at) VALUES (?)", (started_at,)
    )
    conn.commit()
    return cur.lastrowid


def update_run_finish(conn, run_id: int, finished_at: str,
                      files_moved: int, files_skipped: int,
                      files_errored: int, bytes_moved: int):
    conn.execute(
        """UPDATE run_log SET finished_at=?, files_moved=?, files_skipped=?,
           files_errored=?, bytes_moved=? WHERE id=?""",
        (finished_at, files_moved, files_skipped, files_errored, bytes_moved, run_id),
    )
    conn.commit()


def get_recent_moves(conn, days: int = 30) -> list[dict]:
    rows = conn.execute(
        """SELECT * FROM moves
           WHERE moved_at >= datetime('now', ? || ' days')
           ORDER BY moved_at DESC""",
        (f"-{days}",),
    ).fetchall()
    return [dict(r) for r in rows]


def get_stats_by_type(conn, days: int = 30) -> list[dict]:
    rows = conn.execute(
        """SELECT file_type, COUNT(*) as count, SUM(file_size) as total_bytes
           FROM moves
           WHERE status='ok' AND moved_at >= datetime('now', ? || ' days')
           GROUP BY file_type
           ORDER BY count DESC""",
        (f"-{days}",),
    ).fetchall()
    return [dict(r) for r in rows]


def get_daily_totals(conn, days: int = 30) -> list[dict]:
    rows = conn.execute(
        """SELECT date(moved_at) as date,
                  COUNT(*) as file_count,
                  SUM(file_size) as bytes_moved
           FROM moves
           WHERE status='ok' AND moved_at >= datetime('now', ? || ' days')
           GROUP BY date(moved_at)
           ORDER BY date ASC""",
        (f"-{days}",),
    ).fetchall()
    return [dict(r) for r in rows]


def get_summary_stats(conn) -> dict:
    today = conn.execute(
        """SELECT COUNT(*) as count, COALESCE(SUM(file_size), 0) as bytes
           FROM moves WHERE status='ok' AND date(moved_at) = date('now')"""
    ).fetchone()
    month = conn.execute(
        """SELECT COUNT(*) as count, COALESCE(SUM(file_size), 0) as bytes
           FROM moves WHERE status='ok' AND moved_at >= datetime('now', '-30 days')"""
    ).fetchone()
    total = conn.execute(
        """SELECT COUNT(*) as count, COALESCE(SUM(file_size), 0) as bytes
           FROM moves WHERE status='ok'"""
    ).fetchone()
    last_run = conn.execute(
        "SELECT * FROM run_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return {
        "today_count": today["count"],
        "today_bytes": today["bytes"],
        "month_count": month["count"],
        "month_bytes": month["bytes"],
        "total_count": total["count"],
        "total_bytes": total["bytes"],
        "last_run": dict(last_run) if last_run else None,
    }


def get_run_history(conn, limit: int = 20) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM run_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--init":
        import json, os
        cfg_path = Path(__file__).parent.parent / "config.json"
        if not cfg_path.exists():
            cfg_path = Path(__file__).parent.parent / "config.default.json"
        config = json.loads(cfg_path.read_text())
        db_path = os.path.expanduser(config["db_path"])
        conn = get_connection(db_path)
        conn.close()
        print(f"Database initialized at {db_path}")
