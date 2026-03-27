from dataclasses import dataclass

GAME_ICON_FILENAME = "game-icon.svg"


@dataclass(frozen=True)
class GameSpec:
    """Simple metadata for a game module to launch from the base app."""

    id: str
    title: str
    module: str
    available: bool = False


GAME_REGISTRY: tuple[GameSpec, ...] = (
    GameSpec(
        id="patience",
        title="Patience",
        module="patience.games.patience",
        available=True,
    ),
    GameSpec(
        id="freecell",
        title="FreeCell",
        module="patience.games.freecell",
    ),
)
