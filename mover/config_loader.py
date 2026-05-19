import json
import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass
class Config:
    source_dir: str
    dest_dir: str
    schedule_hour: int
    schedule_minute: int
    min_age_minutes: int
    exclude_extensions: list[str]
    dashboard_port: int
    db_path: str
    log_path: str

    def expanded_source_dir(self) -> Path:
        return Path(os.path.expanduser(self.source_dir))

    def expanded_dest_dir(self) -> Path:
        return Path(os.path.expanduser(self.dest_dir))

    def expanded_db_path(self) -> str:
        return os.path.expanduser(self.db_path)

    def expanded_log_path(self) -> str:
        return os.path.expanduser(self.log_path)


def load(config_path: str | None = None) -> Config:
    project_root = Path(__file__).parent.parent
    defaults_path = project_root / "config.default.json"
    user_path = Path(config_path) if config_path else project_root / "config.json"

    data = json.loads(defaults_path.read_text())
    if user_path.exists():
        data.update(json.loads(user_path.read_text()))

    _validate(data)
    return Config(**{k: data[k] for k in Config.__dataclass_fields__})


def _validate(data: dict):
    required = ["source_dir", "dest_dir", "schedule_hour", "schedule_minute",
                 "min_age_minutes", "dashboard_port", "db_path", "log_path"]
    for key in required:
        if key not in data:
            raise ConfigError(f"Missing required config key: {key}")

    if not (0 <= data["schedule_hour"] <= 23):
        raise ConfigError("schedule_hour must be 0-23")
    if not (0 <= data["schedule_minute"] <= 59):
        raise ConfigError("schedule_minute must be 0-59")
    if data["min_age_minutes"] < 0:
        raise ConfigError("min_age_minutes must be >= 0")
    if not (1 <= data["dashboard_port"] <= 65535):
        raise ConfigError("dashboard_port must be 1-65535")
