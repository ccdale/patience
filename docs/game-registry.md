[Previous: window.py notes](window.py.md) | [Index](index.md) | [Next: theme.py notes](theme.py.md)

---

# Code Reading Notes: src/patience/games/registry.py

## Purpose

This file is the central catalog of all games the launcher can show. It defines:

1. A shared icon filename convention (`GAME_ICON_FILENAME`)
2. A typed metadata model for games (`GameSpec`)
3. The actual list of registered games (`GAME_REGISTRY`)

In practice, this is the single source of truth for launcher discovery. If a game is not listed here, it does not appear in the launcher.

## Line-by-Line Reasoning

### Imports and Constants

```python
from dataclasses import dataclass

GAME_ICON_FILENAME = "game-icon.svg"
```

- `dataclass` is used to define a compact immutable data model for game metadata.
- `GAME_ICON_FILENAME` establishes one convention for icon asset naming across all games.
- Keeping icon filename in one constant avoids hard-coded repeated string literals across files.

Design reason: if icon naming ever changes, update one constant instead of many call sites.

---

### `GameSpec` Dataclass

```python
@dataclass(frozen=True)
class GameSpec:
    """Simple metadata for a game module to launch from the base app."""

    id: str
    title: str
    module: str
    available: bool = False
```

Field semantics:

- `id`: Internal stable identifier used in tests/logic (`"patience"`, `"freecell"`, etc.).
- `title`: User-facing display name shown in launcher tiles.
- `module`: Python import path used for dynamic loading (for example `patience.games.freecell`).
- `available`: Feature-flag style toggle. Defaults to `False` so unready games are opt-in.

Key design choice: `frozen=True` makes `GameSpec` immutable after creation.

Why immutability matters here:

1. Registry entries are configuration data, not runtime mutable state.
2. Prevents accidental mutation (for example toggling `available` at runtime by mistake).
3. Makes behavior easier to reason about since entries are stable after module import.

---

### `GAME_REGISTRY`

```python
GAME_REGISTRY: tuple[GameSpec, ...] = (
    GameSpec(...patience...),
    GameSpec(...cruel...),
    GameSpec(...demon...),
    GameSpec(...freecell...),
)
```

- Typed as `tuple[GameSpec, ...]` rather than list.
- Tuple reinforces the "static configuration" idea (registry should not be mutated dynamically).
- Each entry provides complete metadata needed by launcher code.

Current entries:

1. `patience` -> `patience.games.patience`
2. `cruel` -> `patience.games.cruel`
3. `demon` -> `patience.games.demon`
4. `freecell` -> `patience.games.freecell`

All are `available=True`, so all are currently launchable.

## How Launcher Uses This File

The launcher iterates `GAME_REGISTRY`, creating one tile per entry. For each entry it:

1. Displays `title`
2. Uses `module` as technical detail text
3. Enables/disables Launch button from `available`
4. Imports the module dynamically via `importlib.import_module(module)` on click
5. Looks for `game-icon.svg` via `GAME_ICON_FILENAME`

This means registry data drives both UI presentation and runtime behavior.

## Mental Model

Think of this file as a manifest.

- `GameSpec` defines the schema for each row.
- `GAME_REGISTRY` is the data table.
- The launcher is a generic renderer/executor over that table.

Because of that split, adding a game usually requires no launcher code changes. You add a new package and append one `GameSpec` entry.

## Architectural Patterns and Why They Work

### 1. Manifest-driven plugin discovery

The launcher is decoupled from specific game implementations. It only needs the metadata contract. This keeps launcher logic simple and stable while games evolve independently.

### 2. Immutable configuration objects

`frozen=True` and tuple storage both signal that registry data is static configuration, reducing accidental state bugs.

### 3. Safe default for unfinished games

`available=False` default makes partial registration safer. You can stage game metadata before wiring launch behavior without exposing a broken entry.

### 4. Centralized asset convention

`GAME_ICON_FILENAME` standardizes icon lookup and keeps packaging expectations explicit.

## Practical Notes for Future Changes

1. To add a new game, append one `GameSpec` entry to `GAME_REGISTRY`.
2. Keep `id` unique and stable; tests likely rely on uniqueness.
3. Set `available=True` only when module import and `launch(parent_window)` are ready.
4. Ensure game package includes `game-icon.svg` if you want a custom icon.
5. Keep module paths importable (e.g., `patience.games.<name>`).

## Key Takeaways

1. This file is intentionally small but high-leverage: most launcher behavior starts from this metadata.
2. Type hints and immutability make the registry predictable and self-documenting.
3. The registry pattern gives extensibility without changing launcher architecture.
4. `available` acts as a release toggle for game modules.
5. The icon filename constant avoids repeated string coupling across files.

---

[Previous: window.py notes](window.py.md) | [Index](index.md) | [Next: theme.py notes](theme.py.md)
