from dataclasses import FrozenInstanceError

import pytest

from patience.games.registry import GAME_REGISTRY, GameSpec


def test_registry_entries_are_gamespec() -> None:
    assert GAME_REGISTRY
    assert all(isinstance(game, GameSpec) for game in GAME_REGISTRY)


def test_registry_has_unique_ids() -> None:
    ids = [game.id for game in GAME_REGISTRY]
    assert len(ids) == len(set(ids))


def test_registry_modules_use_expected_namespace() -> None:
    assert all(game.module.startswith("patience.games.") for game in GAME_REGISTRY)


def test_gamespec_is_frozen_dataclass() -> None:
    game = GAME_REGISTRY[0]
    with pytest.raises(FrozenInstanceError):
        game.title = "Changed"
