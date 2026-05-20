# Downloads & Documents → OneDrive Backup

Automatically uploads files and folders from `~/Downloads` and `~/Documents` (and any other folders you configure) directly to **OneDrive cloud** every night via the Microsoft Graph API, then deletes the local copies — freeing up storage on your Mac immediately.

No OneDrive desktop app required.

---

## How it works

1. A **nightly job** (via macOS launchd at 2 AM) uploads every file and folder from your configured source directories to OneDrive via the Microsoft Graph API.
2. After each successful upload, the local copy is **deleted** — storage is freed right away.
3. Files modified in the last 5 minutes (still in use) and partial download files (`.crdownload`, `.part`, etc.) are skipped.
4. A **local dashboard** at `http://localhost:7474` shows upload stats, charts, and a 30-day history log.

OneDrive structure after a run:
```
Mac-Backup/
  Downloads/   ← contents of ~/Downloads
  Documents/   ← contents of ~/Documents
```

---

## One-time Azure App Registration (~5 minutes)

This lets the app authenticate with your Microsoft/OneDrive account. You only do this once.

1. Go to [portal.azure.com](https://portal.azure.com) → sign in with your Microsoft account
2. Search for **"App registrations"** → click **New registration**
3. Name: `Mac Backup` (anything works)
4. Supported account types: **Personal Microsoft accounts only**
5. Redirect URI: choose **Mobile and desktop applications**, enter:
   ```
   https://login.microsoftonline.com/common/oauth2/nativeclient
   ```
6. Click **Register**
7. Copy the **Application (client) ID** shown on the overview page
8. Go to **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated permissions**
9. Add: `Files.ReadWrite` → click **Add permissions**

No client secret is needed — this uses the device-code (public client) flow.

---

## Installation

```bash
git clone <repo-url> ~/file_backup_claude_code
cd ~/file_backup_claude_code

# Install dependencies and register the nightly schedule
bash scripts/install.sh

# Add your Azure client_id to config.json
nano config.json

# One-time Microsoft account login (cached forever after)
bash scripts/login.sh
```

---

## Configuration (`config.json`)

| Key | Default | Description |
|-----|---------|-------------|
| `source_dirs` | `["~/Downloads", "~/Documents"]` | Folders to back up (files and subfolders are moved) |
| `onedrive_dest_dir` | `Mac-Backup` | Folder name in your OneDrive root |
| `client_id` | `""` | Azure app client ID (required — see setup above) |
| `schedule_hour` | `2` | Hour to run (0–23) |
| `schedule_minute` | `0` | Minute to run |
| `min_age_minutes` | `5` | Skip items modified in the last N minutes |
| `exclude_extensions` | `.crdownload .part .download .tmp` | File extensions to skip |
| `dashboard_port` | `7474` | Local port for the dashboard |

To add more folders:
```json
"source_dirs": ["~/Downloads", "~/Documents", "~/Desktop"]
```

After editing `config.json`, re-run `bash scripts/install.sh` to reload the schedule.

---

## Usage

```bash
# Start the dashboard
bash scripts/run_dashboard.sh
# Open: http://localhost:7474

# Trigger an immediate upload run (for testing)
curl -X POST http://localhost:7474/api/run-now

# Run directly without the dashboard
.venv/bin/python -m mover.mover

# Check the nightly job is registered
launchctl list | grep downloadsbackup

# View logs
tail -f ~/.local/share/downloadsbackup/mover.log

# Uninstall
bash scripts/uninstall.sh
```

---

## Dashboard

The dashboard at `http://localhost:7474` shows:

- **Stats bar**: items moved today, last 30 days, total GB freed, last run status
- **File type chart**: doughnut breakdown (pdf, zip, folder, dmg, etc.)
- **Daily activity chart**: line chart of moves per day over 30 days
- **Upload log**: every item moved — name, date, size, type, OneDrive path, status
- **Run history**: summary of each nightly run

Auto-refreshes every 60 seconds. **Run Now** button for on-demand uploads.

---

## Troubleshooting

**"Not authenticated" error**
Run `bash scripts/login.sh` again.

**`client_id` not set**
Edit `config.json` and add your Azure Application (client) ID from portal.azure.com.

**Files not being deleted after upload**
Check `~/.local/share/downloadsbackup/mover.log` — an upload error keeps the local file safe.

**Verify the schedule is active**
```bash
launchctl list | grep downloadsbackup
```

**Re-run install after any config change**
```bash
bash scripts/install.sh
```

---

## Privacy & Data

- The only outbound connections are to `graph.microsoft.com` (file uploads) and `login.microsoftonline.com` (auth).
- The SQLite database stores file names, sizes, and timestamps — no file contents.
- The token cache at `~/.local/share/downloadsbackup/token_cache.json` holds your refresh token — keep it private (it stays in your home directory, never committed to this repo).
