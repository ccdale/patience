# Patience

Base GTK4 application for launching solitaire games.

## Architecture

- `patience.app`: GTK `Application` bootstrap
- `patience.window`: Base launcher window UI
- `patience.games.registry`: game metadata for launchable sub-app modules

Each solitaire game should be implemented as a separate package/module (for example `patience.games.klondike`) and then registered in `GAME_REGISTRY`.

## Development

Create environment and install editable package:

```bash
uv venv .venv
uv pip install --python .venv/bin/python -e .
```

Run the base application:

```bash
uv run patience
```
