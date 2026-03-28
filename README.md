# Patience

A GTK4 solitaire application featuring multiple classic card games.

## Documentation

Code-reading and architecture notes are available in the [Documentation Index](docs/index.md).

## Games

### Patience (Klondike)
The classic solitaire game. Deal from the stock pile (one or three cards at a time), build suits in the foundation, and arrange tableau cards in descending order by alternating colors.

### Cruel
A variant using all 52 cards. 12 tableau piles of 4 cards each, with aces automatically moved to foundations. Build tableau sequences in descending order of the same suit. Redeal to regroup when stuck.

### Demon
The British game also known as Canfield. Start with a 13-card reserve, a base card that sets the foundation rank, four tableau piles, and a draw-3 stock. Build tableau piles down by alternating colors with wraparound and build foundations up by suit from the base rank.

### FreeCell
An open-information solitaire with four free cells, four foundations, and eight tableau columns. Build tableau piles down by alternating colors, use free cells and empty columns as temporary storage, and move all cards to the foundations.

## Architecture

- `patience.app`: GTK `Application` bootstrap
- `patience.window`: Launcher window UI listing available games
- `patience.games.registry`: Game metadata for launchable sub-app modules
- `patience.ui`: Shared UI components (card widgets, pile layouts)

Each solitaire game is implemented as a separate module and registered in the game registry for launching.

## Development

Create environment and install editable package:

```bash
uv venv .venv
uv pip install --python .venv/bin/python -e .
```

Run the application:

```bash
uv run patience
```

Run tests:

```bash
uv run pytest -q
```

## Adding Games

New games are designed as small packages under `src/patience/games/`.

1. Create a package directory such as `src/patience/games/demon/`.
2. Add `game.py` with the game state, pure rule helpers, a GTK window class, and a `launch(parent_window)` entry point.
3. Add `__init__.py` that re-exports `launch`, because the launcher imports the package module from the registry.
4. Add a `game-icon.svg` file in the package. The launcher looks for that exact filename via `importlib.resources`.
5. Register the game in `patience.games.registry` with a unique `id`, user-facing `title`, module path, and `available=True` once it is launchable.
6. Add tests in `tests/test_<game>_game.py` for the setup and core move rules.
7. Update this README with a short player-facing description of the new game.

Implementation notes:

- Card logic is built on `ccacards`, especially `Card`, `Pack`, and `Pile`.
- Shared GTK card and pile widgets live in `patience.ui.cards` and `patience.ui.piles`.
- If the game needs assets beyond code, keep them inside the game package so wheel builds can include them naturally.
- Keep rule logic testable outside the window class where possible; existing games use pure helper functions for move validation and dealing.

Contributor checklist:

- Confirm the new package exports `launch` and includes `game-icon.svg`.
- Make sure the registry entry points at the package module, not directly at `game.py`.
- Keep all card setup and move rules expressed in terms of `ccacards` primitives so tests stay simple.
- Add or update README text for both player-facing rules and contributor-facing implementation details.
- Run at least the new game's tests plus `tests/test_registry.py` before considering the game wired up.

## Attribution

Built with the assistance of [GitHub Copilot](https://github.com/features/copilot), which provided guidance on GTK4 API usage, application architecture, and game logic implementation.

## License

This project is licensed under the GNU General Public License v3.0 or later. See the [LICENSE](LICENSE) file for details.
