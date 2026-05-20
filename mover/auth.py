import sys
from pathlib import Path

import msal

SCOPES = ["Files.ReadWrite"]
AUTHORITY = "https://login.microsoftonline.com/common"


def _build_app(client_id: str, cache: msal.SerializableTokenCache) -> msal.PublicClientApplication:
    return msal.PublicClientApplication(client_id, authority=AUTHORITY, token_cache=cache)


def _load_cache(cache_path: str) -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    p = Path(cache_path)
    if p.exists():
        cache.deserialize(p.read_text())
    return cache


def _save_cache(cache: msal.SerializableTokenCache, cache_path: str):
    if cache.has_state_changed:
        p = Path(cache_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(cache.serialize())


def get_token(config) -> str:
    cache = _load_cache(config.expanded_token_cache_path())
    app = _build_app(config.client_id, cache)
    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
    _save_cache(cache, config.expanded_token_cache_path())
    if not result or "access_token" not in result:
        raise RuntimeError(
            "Not authenticated or token expired. Run: bash scripts/login.sh"
        )
    return result["access_token"]


def login(config):
    if not config.client_id:
        print("ERROR: client_id is empty in config.json.")
        print("Please register an Azure app and add the client_id to config.json.")
        print("See README.md for step-by-step instructions.")
        sys.exit(1)

    cache = _load_cache(config.expanded_token_cache_path())
    app = _build_app(config.client_id, cache)
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError(f"Failed to create device flow: {flow.get('error_description', flow)}")

    print("\n" + "=" * 60)
    print(flow["message"])
    print("=" * 60 + "\n")
    print("Waiting for authentication (you have ~15 minutes)...")

    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(f"Authentication failed: {result.get('error_description', result)}")

    _save_cache(cache, config.expanded_token_cache_path())
    print(f"\nSuccess! Token cached at {config.expanded_token_cache_path()}")


if __name__ == "__main__":
    from mover import config_loader
    cfg = config_loader.load()
    login(cfg)
