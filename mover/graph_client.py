import io
from pathlib import Path

import requests

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB — use upload session above this


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def ensure_folder(token: str, folder_path: str):
    """Create a folder (and all parent folders) in OneDrive if it doesn't exist.
    folder_path is relative to drive root, e.g. 'Mac-Backup/Downloads'.
    """
    parts = folder_path.strip("/").split("/")
    for i in range(1, len(parts) + 1):
        path = "/".join(parts[:i])
        parent = "/".join(parts[:i - 1]) if i > 1 else None
        if parent:
            url = f"{GRAPH_BASE}/me/drive/root:/{parent}:/children"
        else:
            url = f"{GRAPH_BASE}/me/drive/root/children"
        requests.post(
            url,
            headers={**_headers(token), "Content-Type": "application/json"},
            json={
                "name": parts[i - 1],
                "folder": {},
                "@microsoft.graph.conflictBehavior": "rename",
            },
        )


def _item_exists(token: str, onedrive_path: str) -> bool:
    resp = requests.get(
        f"{GRAPH_BASE}/me/drive/root:/{onedrive_path}",
        headers=_headers(token),
    )
    return resp.status_code == 200


def _resolve_dest_name(token: str, parent_path: str, name: str) -> str:
    stem = Path(name).stem
    suffix = Path(name).suffix
    candidate = name
    n = 1
    while _item_exists(token, f"{parent_path}/{candidate}"):
        candidate = f"{stem}_{n}{suffix}"
        n += 1
    return candidate


def upload_file(token: str, local_path: Path, onedrive_folder: str) -> str:
    """Upload a single file. Returns the OneDrive path where it was stored."""
    safe_name = _resolve_dest_name(token, onedrive_folder, local_path.name)
    dest_path = f"{onedrive_folder}/{safe_name}"
    file_size = local_path.stat().st_size

    if file_size <= CHUNK_SIZE:
        _simple_upload(token, local_path, dest_path)
    else:
        _session_upload(token, local_path, dest_path, file_size)

    return dest_path


def upload_folder(token: str, local_path: Path, onedrive_parent: str) -> str:
    """Recursively upload a folder to OneDrive. Returns the OneDrive path."""
    safe_name = _resolve_dest_name(token, onedrive_parent, local_path.name)
    dest_folder = f"{onedrive_parent}/{safe_name}"
    ensure_folder(token, dest_folder)
    _upload_folder_contents(token, local_path, dest_folder)
    return dest_folder


def _upload_folder_contents(token: str, local_dir: Path, onedrive_folder: str):
    for item in local_dir.iterdir():
        if item.is_file():
            upload_file(token, item, onedrive_folder)
        elif item.is_dir():
            sub_dest = f"{onedrive_folder}/{item.name}"
            ensure_folder(token, sub_dest)
            _upload_folder_contents(token, item, sub_dest)


def _simple_upload(token: str, local_path: Path, dest_path: str):
    url = f"{GRAPH_BASE}/me/drive/root:/{dest_path}:/content"
    with open(local_path, "rb") as f:
        resp = requests.put(
            url,
            headers={**_headers(token), "Content-Type": "application/octet-stream"},
            data=f,
        )
    resp.raise_for_status()


def _session_upload(token: str, local_path: Path, dest_path: str, file_size: int):
    session_url = f"{GRAPH_BASE}/me/drive/root:/{dest_path}:/createUploadSession"
    resp = requests.post(
        session_url,
        headers={**_headers(token), "Content-Type": "application/json"},
        json={"item": {"@microsoft.graph.conflictBehavior": "rename"}},
    )
    resp.raise_for_status()
    upload_url = resp.json()["uploadUrl"]

    with open(local_path, "rb") as f:
        offset = 0
        while offset < file_size:
            chunk = f.read(CHUNK_SIZE)
            end = offset + len(chunk) - 1
            resp = requests.put(
                upload_url,
                headers={
                    "Content-Range": f"bytes {offset}-{end}/{file_size}",
                    "Content-Length": str(len(chunk)),
                },
                data=chunk,
            )
            resp.raise_for_status()
            offset += len(chunk)
