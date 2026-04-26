import json

import pytest

from patience.stats import load_stats, record_started, record_won


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))


def test_load_stats_returns_zeros_when_no_file_exists() -> None:
    assert load_stats("mygame") == (0, 0)


def test_record_started_increments_started() -> None:
    assert record_started("mygame") == (1, 0)
    assert record_started("mygame") == (2, 0)
    assert record_started("mygame") == (3, 0)


def test_record_won_increments_won() -> None:
    record_started("mygame")
    assert record_won("mygame") == (1, 1)
    assert record_won("mygame") == (1, 2)


def test_record_won_does_not_change_started() -> None:
    record_started("mygame")
    record_started("mygame")
    started, won = record_won("mygame")
    assert started == 2
    assert won == 1


def test_load_stats_reflects_persisted_values() -> None:
    record_started("mygame")
    record_started("mygame")
    record_won("mygame")
    assert load_stats("mygame") == (2, 1)


def test_games_are_tracked_independently() -> None:
    record_started("game_a")
    record_started("game_a")
    record_won("game_a")

    record_started("game_b")

    assert load_stats("game_a") == (2, 1)
    assert load_stats("game_b") == (1, 0)


def test_stats_file_is_written_as_valid_json(tmp_path) -> None:
    record_started("mygame")
    record_won("mygame")
    stats_file = tmp_path / "patience" / "mygame.stats"
    assert stats_file.exists()
    data = json.loads(stats_file.read_text())
    assert data == {"started": 1, "won": 1}


def test_load_stats_returns_zeros_on_corrupt_file(tmp_path) -> None:
    stats_dir = tmp_path / "patience"
    stats_dir.mkdir()
    (stats_dir / "mygame.stats").write_text("not valid json")
    assert load_stats("mygame") == (0, 0)


def test_load_stats_tolerates_missing_keys(tmp_path) -> None:
    stats_dir = tmp_path / "patience"
    stats_dir.mkdir()
    (stats_dir / "mygame.stats").write_text(json.dumps({}))
    assert load_stats("mygame") == (0, 0)


def test_load_stats_tolerates_partial_keys(tmp_path) -> None:
    stats_dir = tmp_path / "patience"
    stats_dir.mkdir()
    (stats_dir / "mygame.stats").write_text(json.dumps({"started": 5}))
    assert load_stats("mygame") == (5, 0)
