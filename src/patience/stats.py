import json
import os
from pathlib import Path


def _stats_path(game_id: str) -> Path:
    xdg_data_home = os.environ.get("XDG_DATA_HOME") or str(
        Path.home() / ".local" / "share"
    )
    data_dir = Path(xdg_data_home) / "patience"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / f"{game_id}.stats"


def load_stats(game_id: str) -> tuple[int, int]:
    """Return (started, won) for *game_id*."""
    path = _stats_path(game_id)
    if not path.exists():
        return 0, 0
    try:
        data = json.loads(path.read_text())
        return int(data.get("started", 0)), int(data.get("won", 0))
    except (json.JSONDecodeError, ValueError, OSError):
        return 0, 0


def _save_stats(game_id: str, started: int, won: int) -> None:
    _stats_path(game_id).write_text(json.dumps({"started": started, "won": won}))


def record_started(game_id: str) -> tuple[int, int]:
    """Increment the started count and return updated (started, won)."""
    started, won = load_stats(game_id)
    started += 1
    _save_stats(game_id, started, won)
    return started, won


def record_won(game_id: str) -> tuple[int, int]:
    """Increment the won count and return updated (started, won)."""
    started, won = load_stats(game_id)
    won += 1
    _save_stats(game_id, started, won)
    return started, won
