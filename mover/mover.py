import logging
import os
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path

from mover import auth, config_loader, db, graph_client


@dataclass
class RunSummary:
    files_moved: int = 0
    files_skipped: int = 0
    files_errored: int = 0
    bytes_moved: int = 0


def _setup_logging(log_path: str):
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(),
        ],
    )


def _is_safe_to_move(path: Path, min_age_minutes: int) -> bool:
    age_seconds = time.time() - path.stat().st_mtime
    return age_seconds >= min_age_minutes * 60


def _is_excluded(path: Path, exclude_extensions: list[str]) -> bool:
    return path.suffix.lower() in [e.lower() for e in exclude_extensions]


def run_mover(config, conn) -> RunSummary:
    log = logging.getLogger(__name__)
    summary = RunSummary()
    now_utc = datetime.now(timezone.utc).isoformat()
    run_id = db.insert_run_start(conn, now_utc)

    try:
        token = auth.get_token(config)
    except RuntimeError as e:
        log.error(str(e))
        db.update_run_finish(conn, run_id, datetime.now(timezone.utc).isoformat(), 0, 0, 1, 0)
        return summary

    log.info("Ensuring OneDrive folder '%s' exists", config.onedrive_folder)
    graph_client.ensure_folder(token, config.onedrive_folder)

    source_dir = config.expanded_source_dir()
    if not source_dir.exists():
        log.error("Source directory does not exist: %s", source_dir)
        db.update_run_finish(conn, run_id, datetime.now(timezone.utc).isoformat(), 0, 0, 1, 0)
        return summary

    files = [p for p in source_dir.iterdir() if p.is_file()]
    log.info("Found %d files in %s", len(files), source_dir)

    for path in files:
        moved_at = datetime.now(timezone.utc).isoformat()
        file_size = path.stat().st_size
        file_type = path.suffix.lstrip(".").lower() or "no_ext"

        if _is_excluded(path, config.exclude_extensions):
            log.info("SKIP %s (excluded extension)", path.name)
            db.insert_move(conn, filename=path.name, source_path=str(path),
                           dest_path="", file_size=file_size, file_type=file_type,
                           moved_at=moved_at, status="skipped", error_msg="excluded extension")
            summary.files_skipped += 1
            continue

        if not _is_safe_to_move(path, config.min_age_minutes):
            log.info("SKIP %s (modified within last %d min)", path.name, config.min_age_minutes)
            db.insert_move(conn, filename=path.name, source_path=str(path),
                           dest_path="", file_size=file_size, file_type=file_type,
                           moved_at=moved_at, status="skipped",
                           error_msg=f"modified within last {config.min_age_minutes} min")
            summary.files_skipped += 1
            continue

        try:
            dest_path = graph_client.upload_file(token, path, config.onedrive_folder)
            os.remove(path)
            log.info("MOVED %s → OneDrive:%s (%d bytes)", path.name, dest_path, file_size)
            db.insert_move(conn, filename=path.name, source_path=str(path),
                           dest_path=dest_path, file_size=file_size, file_type=file_type,
                           moved_at=moved_at, status="ok")
            summary.files_moved += 1
            summary.bytes_moved += file_size
        except Exception as exc:
            log.error("ERROR %s: %s", path.name, exc)
            db.insert_move(conn, filename=path.name, source_path=str(path),
                           dest_path="", file_size=file_size, file_type=file_type,
                           moved_at=moved_at, status="error", error_msg=str(exc))
            summary.files_errored += 1

    finished_at = datetime.now(timezone.utc).isoformat()
    db.update_run_finish(conn, run_id, finished_at, summary.files_moved,
                         summary.files_skipped, summary.files_errored, summary.bytes_moved)
    log.info("Run complete: moved=%d skipped=%d errors=%d bytes=%d",
             summary.files_moved, summary.files_skipped,
             summary.files_errored, summary.bytes_moved)
    return summary


if __name__ == "__main__":
    config = config_loader.load()
    _setup_logging(config.expanded_log_path())
    conn = db.get_connection(config.expanded_db_path())
    try:
        run_mover(config, conn)
    finally:
        conn.close()
