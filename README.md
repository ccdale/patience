# Patience

A GTK4 solitaire application featuring multiple classic card games.

## Games

### Patience (Klondike)
The classic solitaire game. Deal from the stock pile (one or three cards at a time), build suits in the foundation, and arrange tableau cards in descending order by alternating colors.

### Cruel
A variant using all 52 cards. 12 tableau piles of 4 cards each, with aces automatically moved to foundations. Build tableau sequences in descending order of the same suit. Redeal to regroup when stuck.

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

## Attribution

Built with the assistance of [GitHub Copilot](https://github.com/features/copilot), which provided guidance on GTK4 API usage, application architecture, and game logic implementation.

## License

This project is licensed under the GNU General Public License v3.0 or later. See the [LICENSE](LICENSE) file for details.
