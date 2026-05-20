import logging
import shutil
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


def _folder_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _is_safe_to_move(path: Path, min_age_minutes: int) -> bool:
    """For folders, check that no file inside was modified recently."""
    min_age_seconds = min_age_minutes * 60
    if path.is_dir():
        return all(
            time.time() - f.stat().st_mtime >= min_age_seconds
            for f in path.rglob("*") if f.is_file()
        )
    return time.time() - path.stat().st_mtime >= min_age_seconds


def _is_excluded(path: Path, exclude_extensions: list[str]) -> bool:
    if path.is_dir():
        return False
    return path.suffix.lower() in [e.lower() for e in exclude_extensions]


def _process_source(token: str, source_dir: Path, onedrive_folder: str,
                    config, conn, summary: RunSummary, log):
    """Upload and delete all top-level files and folders in source_dir."""
    if not source_dir.exists():
        log.error("Source directory does not exist: %s", source_dir)
        return

    graph_client.ensure_folder(token, onedrive_folder)
    items = list(source_dir.iterdir())
    log.info("Found %d items in %s", len(items), source_dir)

    for path in items:
        moved_at = datetime.now(timezone.utc).isoformat()
        is_dir = path.is_dir()
        item_size = _folder_size(path) if is_dir else path.stat().st_size
        file_type = "folder" if is_dir else (path.suffix.lstrip(".").lower() or "no_ext")

        if _is_excluded(path, config.exclude_extensions):
            log.info("SKIP %s (excluded extension)", path.name)
            db.insert_move(conn, filename=path.name, source_path=str(path),
                           dest_path="", file_size=item_size, file_type=file_type,
                           moved_at=moved_at, status="skipped", error_msg="excluded extension")
            summary.files_skipped += 1
            continue

        if not _is_safe_to_move(path, config.min_age_minutes):
            log.info("SKIP %s (modified within last %d min)", path.name, config.min_age_minutes)
            db.insert_move(conn, filename=path.name, source_path=str(path),
                           dest_path="", file_size=item_size, file_type=file_type,
                           moved_at=moved_at, status="skipped",
                           error_msg=f"modified within last {config.min_age_minutes} min")
            summary.files_skipped += 1
            continue

        try:
            if is_dir:
                dest_path = graph_client.upload_folder(token, path, onedrive_folder)
                shutil.rmtree(str(path))
            else:
                dest_path = graph_client.upload_file(token, path, onedrive_folder)
                path.unlink()

            log.info("MOVED %s → OneDrive:%s (%d bytes)", path.name, dest_path, item_size)
            db.insert_move(conn, filename=path.name, source_path=str(path),
                           dest_path=dest_path, file_size=item_size, file_type=file_type,
                           moved_at=moved_at, status="ok")
            summary.files_moved += 1
            summary.bytes_moved += item_size

        except Exception as exc:
            log.error("ERROR %s: %s", path.name, exc)
            db.insert_move(conn, filename=path.name, source_path=str(path),
                           dest_path="", file_size=item_size, file_type=file_type,
                           moved_at=moved_at, status="error", error_msg=str(exc))
            summary.files_errored += 1


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

    for source_dir in config.expanded_source_dirs():
        onedrive_folder = f"{config.onedrive_dest_dir}/{source_dir.name}"
        log.info("--- Processing %s → OneDrive:%s ---", source_dir, onedrive_folder)
        _process_source(token, source_dir, onedrive_folder, config, conn, summary, log)

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
