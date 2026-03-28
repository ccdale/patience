[Previous: piles.py notes](piles.py.md) | [Index](index.md) | [Next: Cruel game deep dive](cruel-game.py.md)

---

# Code Reading Notes: Generic Game Module Pattern

## Purpose

This document describes the shared structure used by game modules under src/patience/games/*/game.py. Even though each game has different rules, the module architecture is intentionally consistent.

Common sections (in order):

1. Imports and GTK version guards
2. Constants
3. State dataclasses
4. Rule/helper functions (pure logic)
5. Initial deal/state construction
6. Window class (UI + interaction)
7. Launch entry point (`launch(parent_window)`) near file end

## 1. Imports Pattern

Typical shape:

```python
from dataclasses import dataclass

import gi
from ccacards.card import Card
from ccacards.pack import Pack
from ccacards.pile import Pile

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

from gi.repository import Gdk, Gtk  # noqa: E402

from patience.ui.cards import build_card_widget, resolve_card_data_dir
from patience.ui.help import build_rules_panel
from patience.ui.piles import ...
```

Why this pattern exists:

- `ccacards` provides game primitives (`Card`, `Pack`, `Pile`).
- `gi.require_version(...)` must appear before GTK imports.
- `# noqa: E402` suppresses import-order lint where required by PyGObject conventions.
- Shared UI helpers are imported instead of duplicating widget code.

## 2. Constants Pattern

Each module defines game-specific constants at top-level, such as:

- draw count (`DRAW_COUNT`)
- number of columns (`TABLEAU_COLS`)
- free-cell/reserve sizes
- display labels and rank names

Design intent: constants make rule configuration obvious and easy to test.

## 3. State Dataclasses Pattern

Most games define:

1. A frozen state dataclass (for pile groupings)
2. A mutable selection dataclass (for current user selection)

Example shape:

```python
@dataclass(frozen=True)
class SomeGameState:
    stock: Pile
    waste: Pile
    foundations: tuple[Pile, Pile, Pile, Pile]
    tableau: tuple[Pile, ...]

@dataclass
class Selection:
    source: str
    pile_index: int
    start_index: int | None = None
```

Why this split:

- State object defines the board model clearly.
- Selection object tracks transient UI interaction separately from static board structure.

## 4. Rules Layer Pattern (Pure Functions)

Each game keeps core legality checks in standalone functions, for example:

- `can_place_on_foundation(...)`
- `can_place_on_tableau(...)`
- `is_valid_tableau_run(...)`
- game-specific utilities (e.g., move-capacity or mandatory reserve fill)

Key property: these functions are mostly GTK-independent and easy to unit test.

## 5. Initial State Construction Pattern

A `create_initial_state()` function typically:

1. Creates and shuffles a `Pack`
2. Creates empty `Pile` containers
3. Deals cards according to variant rules
4. Normalizes face-up/face-down orientation
5. Returns the state dataclass

Reasoning:

- Keeps deal/setup logic in one place.
- Makes "new game" behavior a simple reset to `create_initial_state()`.

## 6. Window Class Pattern

Each game has one main window class extending `Gtk.ApplicationWindow`.

Common constructor responsibilities:

1. Set title and default size
2. Add `table-window` CSS class
3. Set transient parent when launched from launcher
4. Initialize `_state`, `_selection`, `_card_data_dir`
5. Install selection CSS for highlights
6. Build root layout: header, status line, rules panel, board container
7. Call `_refresh_board()` and attach root to window

Typical instance fields:

- `_state`: game board model
- `_selection`: current selected pile/card/run
- `_status`: status label for user feedback
- `_board`: container rebuilt after moves
- `_card_data_dir`: resolved image directory for card rendering

## 7. Board Rendering Pattern

Most modules include:

- `_refresh_board()`
- `_build_board()` or `_build_board_grid()`
- `_card_widget()` wrapper around `build_card_widget(...)`

`_refresh_board()` pattern:

1. Remove existing child(ren) from board container
2. Rebuild board widget from current state
3. Append rebuilt widget

Why this pattern works here:

- Simpler than incremental mutation for card-table layouts.
- Keeps state→UI mapping deterministic after each action.

## 8. Interaction/Move Handler Pattern

Event handlers usually follow this sequence:

1. Determine source/destination from click
2. Resolve current selection state
3. Validate move with pure rule functions
4. Mutate underlying piles if legal
5. Apply post-move automation if variant requires it
6. Clear/adjust selection and status text
7. Refresh board

Examples of handlers:

- `_on_stock_clicked`
- `_on_tableau_clicked`
- `_on_foundation_clicked`
- `_on_new_game_clicked`

## 9. Styling and Selection Pattern

Each game window typically defines local CSS installer for selection visuals (`selected-pile`, `selected-card`) and relies on global theme classes for broader look.

Layering model:

1. Global theme module handles table/panel baseline visual style.
2. Game module handles selection-specific highlights.
3. Shared UI builders assign CSS classes; game CSS/theme CSS make them visible.

## 10. Launch Entry Point Pattern

Near file end, each module exposes a `launch(parent_window)` function, which:

1. Retrieves app object from parent window
2. Constructs the game window
3. Presents it

This is the contract expected by the launcher module via dynamic import.

## Generic Skeleton (Template)

```python
# imports + gi.require_version + gtk imports

# constants

@dataclass(frozen=True)
class GameState:
    ...

@dataclass
class Selection:
    ...

# pure rule functions

def create_initial_state() -> GameState:
    ...

class SomeGameWindow(Gtk.ApplicationWindow):
    def __init__(...):
        ...

    def _refresh_board(self) -> None:
        ...

    def _build_board(self) -> Gtk.Widget:
        ...

    # click handlers


def launch(parent_window: Gtk.Window) -> None:
    ...
```

## What Changes Between Games

Stable across modules:

1. Overall file shape and UI assembly flow
2. Selection/refresh model
3. Use of shared UI helpers
4. Launcher contract (`launch(parent_window)`)

Variant-specific:

1. State structure (free cells, reserve, stock/waste presence)
2. Legal move rules
3. Initial deal algorithm
4. Automatic move behavior
5. Board geometry and window size
6. Status text and rules copy

## Practical Reading Checklist for Any New Game Module

1. Read constants first to identify variant constraints.
2. Read state dataclass to understand board topology.
3. Read rule helpers to understand legality.
4. Read create_initial_state() to understand deal orientation.
5. Read `_build_board*` to map piles to visible positions.
6. Read click handlers to understand move flow and side effects.
7. Confirm `launch(parent_window)` exists for registry compatibility.

---

[Previous: piles.py notes](piles.py.md) | [Index](index.md) | [Next: Cruel game deep dive](cruel-game.py.md)
