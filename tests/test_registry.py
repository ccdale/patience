from dataclasses import FrozenInstanceError
from importlib import import_module, resources

import pytest

from patience.games.registry import GAME_ICON_FILENAME, GAME_REGISTRY, GameSpec


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


def test_available_games_have_launch_function() -> None:
    for game in GAME_REGISTRY:
        if not game.available:
            continue
        module = import_module(game.module)
        assert callable(getattr(module, "launch", None))


def test_available_games_have_conventional_icon_file() -> None:
    for game in GAME_REGISTRY:
        if not game.available:
            continue
        icon = resources.files(game.module).joinpath(GAME_ICON_FILENAME)
        assert icon.is_file()
