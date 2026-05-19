# Downloads → OneDrive Backup

Automatically moves files from `~/Downloads` to your OneDrive folder every night, freeing up disk space on your Mac. Includes a local web dashboard showing upload history and stats for the last 30 days.

## How it works

1. A **nightly job** (via macOS launchd) runs at 2 AM and moves all files in `~/Downloads` to your OneDrive folder using standard file operations (`shutil.move`).
2. The **OneDrive desktop app** picks up the moved files and syncs them to the cloud automatically — no API or account setup required by this app.
3. A **local dashboard** at `http://localhost:7474` shows stats, charts, and a log of everything that was moved.
4. Files modified in the last 5 minutes (still downloading) and partial download files (`.crdownload`, `.part`, etc.) are automatically skipped.

**Requirement:** The [Microsoft OneDrive desktop app](https://www.microsoft.com/en-us/microsoft-365/onedrive/download) must be installed and signed in on your Mac. It creates a local sync folder (usually `~/Library/CloudStorage/OneDrive-Personal/`) that this app moves files into.

---

## Installation

```bash
git clone <repo-url> ~/file_backup_claude_code
cd ~/file_backup_claude_code

# Install and register the nightly schedule
bash scripts/install.sh
```

That's it. The nightly job is now active.

---

## Configuration (`config.json`)

| Key | Default | Description |
|-----|---------|-------------|
| `source_dir` | `~/Downloads` | Folder to move files from |
| `dest_dir` | `~/Library/CloudStorage/OneDrive-Personal/Downloads-Backup` | OneDrive folder to move files into |
| `schedule_hour` | `2` | Hour to run (0–23, 24-hour clock) |
| `schedule_minute` | `0` | Minute to run |
| `min_age_minutes` | `5` | Skip files modified in the last N minutes |
| `exclude_extensions` | `.crdownload .part .download .tmp` | Extensions to always skip |
| `dashboard_port` | `7474` | Local port for the dashboard |

To find your exact OneDrive folder path, open Finder — it shows up in the sidebar as "OneDrive". Right-click → "Get Info" to see the full path.

After editing `config.json`, re-run `bash scripts/install.sh` to update the schedule.

---

## Usage

```bash
# Start the dashboard (run whenever you want to review stats)
bash scripts/run_dashboard.sh
# Open: http://localhost:7474

# Trigger an immediate run (for testing)
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
- **File type chart**: doughnut breakdown of what kinds of files were moved
- **Daily activity chart**: line chart of moves per day over 30 days
- **Move log**: table of every file — name, date, size, type, OneDrive path, status
- **Run history**: summary of each nightly run (moved / skipped / errors)

The dashboard auto-refreshes every 60 seconds. Use the **Run Now** button for an on-demand run.

---

## Troubleshooting

**OneDrive folder not found**
Check your actual OneDrive path in Finder and update `dest_dir` in `config.json`. Common paths:
- `~/Library/CloudStorage/OneDrive-Personal/`
- `~/OneDrive/`

**Files not being moved**
- Check `~/.local/share/downloadsbackup/mover.log` for errors
- Verify the nightly job is active: `launchctl list | grep downloadsbackup`

**Re-run install after config change**
```bash
bash scripts/install.sh
```

**Dashboard won't start**
Check the port isn't in use: `lsof -i :7474`
