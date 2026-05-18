from pathlib import Path

import requests

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB threshold for upload session


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def ensure_folder(token: str, folder_name: str):
    url = f"{GRAPH_BASE}/me/drive/root/children"
    requests.post(
        url,
        headers={**_headers(token), "Content-Type": "application/json"},
        json={
            "name": folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename",
        },
    )


def _resolve_dest_name(token: str, folder_name: str, filename: str) -> str:
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    name = filename
    n = 1
    while True:
        url = f"{GRAPH_BASE}/me/drive/root:/{folder_name}/{name}"
        resp = requests.get(url, headers=_headers(token))
        if resp.status_code == 404:
            return name
        name = f"{stem}_{n}{suffix}"
        n += 1


def upload_file(token: str, local_path: Path, onedrive_folder: str) -> str:
    safe_name = _resolve_dest_name(token, onedrive_folder, local_path.name)
    dest_path = f"{onedrive_folder}/{safe_name}"

    file_size = local_path.stat().st_size
    if file_size <= CHUNK_SIZE:
        _simple_upload(token, local_path, dest_path)
    else:
        _session_upload(token, local_path, dest_path, file_size)

    return dest_path


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
