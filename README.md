# Downloads → OneDrive Backup

Automatically uploads files from `~/Downloads` to OneDrive every night, freeing up disk space on your Mac. Includes a local web dashboard showing upload history and stats for the last 30 days.

## How it works

1. A **nightly job** (via macOS launchd) runs at 2 AM, uploads all files in `~/Downloads` to your OneDrive via the Microsoft Graph API, then deletes the local copies.
2. A **local dashboard** at `http://localhost:7474` shows stats, charts, and a searchable log of everything that was moved.
3. Files modified in the last 5 minutes (still downloading) and partial download files (`.crdownload`, `.part`, etc.) are automatically skipped.

No OneDrive desktop app is required — files go directly to the cloud.

---

## One-time Azure App Registration (5 minutes)

This lets the app authenticate with your Microsoft account.

1. Go to [portal.azure.com](https://portal.azure.com) → **Azure Active Directory** → **App registrations** → **New registration**
2. Name: `Downloads Backup` (anything works)
3. Supported account types: **Accounts in any organizational directory and personal Microsoft accounts**
4. Redirect URI: Select **Mobile and desktop applications**, enter:
   ```
   https://login.microsoftonline.com/common/oauth2/nativeclient
   ```
5. Click **Register**
6. Copy the **Application (client) ID** — you'll paste it into `config.json`
7. Go to **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated permissions**
8. Search for and add: `Files.ReadWrite`
9. Click **Grant admin consent** (if you're a personal account owner, this is automatic)

No client secret is needed — this uses the public client (device code) flow.

---

## Installation

```bash
git clone <repo-url> ~/file_backup_claude_code
cd ~/file_backup_claude_code

# Install dependencies and set up the nightly schedule
bash scripts/install.sh

# Edit config: add your client_id and optionally change the OneDrive folder name
nano config.json

# Authenticate with Microsoft (one-time — tokens are cached)
bash scripts/login.sh
```

---

## Configuration (`config.json`)

| Key | Default | Description |
|-----|---------|-------------|
| `source_dir` | `~/Downloads` | Folder to upload from |
| `onedrive_folder` | `Downloads-Backup` | Folder name in your OneDrive root |
| `client_id` | `""` | Azure app client ID (required) |
| `schedule_hour` | `2` | Hour to run (0–23, 24-hour clock) |
| `schedule_minute` | `0` | Minute to run |
| `min_age_minutes` | `5` | Skip files modified in the last N minutes |
| `exclude_extensions` | `.crdownload .part .download .tmp` | Extensions to always skip |
| `dashboard_port` | `7474` | Local port for the dashboard |

After editing `config.json`, re-run `bash scripts/install.sh` to update the schedule.

---

## Usage

```bash
# Start the dashboard (run this whenever you want to review stats)
bash scripts/run_dashboard.sh
# Open: http://localhost:7474

# Trigger an immediate upload run (useful for testing)
curl -X POST http://localhost:7474/api/run-now
# Or directly (no dashboard needed):
.venv/bin/python -m mover.mover

# Check that the nightly job is registered
launchctl list | grep downloadsbackup

# View logs
tail -f ~/.local/share/downloadsbackup/mover.log

# Uninstall
bash scripts/uninstall.sh
```

---

## Dashboard

The dashboard at `http://localhost:7474` shows:

- **Stats bar**: files moved today, last 30 days, total GB freed, last run status
- **File type chart**: doughnut breakdown of what kinds of files were uploaded
- **Daily activity chart**: line chart of uploads per day over 30 days
- **Upload log**: table of every file — name, date, size, type, OneDrive path, status
- **Run history**: summary of each nightly run (moved / skipped / errors)

The dashboard auto-refreshes every 60 seconds. You can also trigger a manual run from the **Run Now** button.

---

## Troubleshooting

**"Not authenticated" error**
Run `bash scripts/login.sh` again — the token may have expired.

**Files not being moved**
- Check `~/.local/share/downloadsbackup/mover.log` for errors
- Ensure `client_id` is set in `config.json`
- Verify the nightly job is active: `launchctl list | grep downloadsbackup`

**Dashboard won't start**
- Ensure `bash scripts/install.sh` has been run
- Check the port isn't in use: `lsof -i :7474`

**Re-run install after config change**
```bash
bash scripts/install.sh
```
This re-reads `config.json` and reloads the launchd schedule.

---

## Data & Privacy

- All data stays local. The only outbound connection is to `graph.microsoft.com` to upload files and `login.microsoftonline.com` for authentication.
- The SQLite database at `~/.local/share/downloadsbackup/history.db` stores file names, sizes, and timestamps — no file contents.
- The Microsoft token cache at `~/.local/share/downloadsbackup/token_cache.json` contains your refresh token. Keep it private (it's in your home directory, not in this repo).
