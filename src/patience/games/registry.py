from dataclasses import dataclass


@dataclass(frozen=True)
class GameSpec:
    """Simple metadata for a game module to launch from the base app."""

    id: str
    title: str
    module: str
    available: bool = False


GAME_REGISTRY: tuple[GameSpec, ...] = (
    GameSpec(
        id="klondike",
        title="Klondike",
        module="patience.games.klondike",
    ),
    GameSpec(
        id="freecell",
        title="FreeCell",
        module="patience.games.freecell",
    ),
)
