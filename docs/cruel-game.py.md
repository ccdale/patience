[Previous: generic game module pattern](game-module-pattern.md) | [Index](index.md) | [Next: Patience game deep dive](patience-game.py.md)

---

# Code Reading Notes: src/patience/games/cruel/game.py

## Purpose

This module implements the Cruel solitaire variant end-to-end: board state, move rules, GTK window, and launch integration.

Cruel is a good “first game module” to study because:

1. It has no stock/waste draw loop
2. It moves only top cards (no tableau run slicing)
3. Its tableau rule is strict and simple (same suit, one lower)
4. It still shows the full architecture pattern used across games

## How It Maps to the Generic Pattern

This file follows the same sections described in [docs/game-module-pattern.md](docs/game-module-pattern.md):

1. Imports and constants
2. State dataclass
3. Pure rule/helper functions
4. Initial state creation
5. Window class with board building and event handlers
6. Launch entry point

## 1. Imports and Constants

At the top of [src/patience/games/cruel/game.py](src/patience/games/cruel/game.py):

- Imports `Card`, `Pack`, `Pile` from ccacards
- Uses `gi.require_version` before GTK imports
- Pulls in shared UI builders from cards/help/piles modules

Important constants:

- `TABLEAU_COLS = 12`
- `PILE_SIZE = 4`

These encode the core Cruel layout: twelve tableau piles of four cards after aces are extracted.

## 2. State Model

```python
@dataclass(frozen=True)
class CruelState:
    foundations: tuple[Pile, Pile, Pile, Pile]
    tableau: tuple[Pile, ...]  # 12 piles
```

Design notes:

1. The state is compact: foundations + tableau only.
2. No stock/waste/free-cells/reserve, which keeps move flow simple.
3. `frozen=True` signals “shape is fixed,” while individual `Pile` contents remain mutable.

Transient UI selection is separate:

```python
@dataclass
class Selection:
    pile_index: int
```

Only one selected tableau pile index is needed because Cruel only moves top cards.

## 3. Initial Deal Logic

`create_initial_state()` is the setup engine.

Flow:

1. Create and shuffle a pack
2. Build four empty foundation piles and twelve tableau piles
3. Iterate through all 52 cards
4. Flip cards face-up if needed
5. Put aces directly onto foundations
6. Collect non-aces, then deal them into 12 piles of 4

Key behavior:

- Aces are extracted first, so foundations start seeded.
- Remaining 48 cards produce exactly 12 x 4 tableau.

Notable implementation detail:

```python
foundations[len([f for f in foundations if len(f) > 0])].append(card)
```

This places each discovered ace into the next empty foundation pile in order.

## 4. Rule Functions (Pure Logic)

### Foundation rule

`can_place_on_foundation(card, top)`:

1. Empty foundation accepts Ace only
2. Otherwise must match suit and be exactly one rank higher

### Tableau rule

`can_place_on_tableau(card, top)`:

1. Empty destination is not allowed in Cruel
2. Card must be same suit and one rank lower than destination top

This strict rule is what makes Cruel “Cruel.”

### Utility helpers

- `_find_foundation_for(...)`: finds first valid foundation index for a card
- `_collect_auto_moves(...)`: simulates all automatic foundation moves without mutating real state
- `_has_valid_moves(...)`: checks if any legal move remains
- `collect_and_redeal(...)`: gathers tableau cards left-to-right and redeals into groups of four

Why these helpers matter:

1. They keep event handlers readable.
2. They isolate game logic from GTK concerns.
3. They are good targets for unit tests.

## 5. Window Construction

`CruelWindow` in [src/patience/games/cruel/game.py](src/patience/games/cruel/game.py) follows the standard window pattern.

Constructor responsibilities:

1. Configure window title/size and add `table-window` class
2. Attach transient parent when launched from launcher
3. Initialize state, card data dir, selection
4. Install local selection/game-over CSS
5. Build root layout with:
- header (title + Redeal + New Game)
- status label
- shared rules panel
- board container
6. Refresh/render board

This mirrors other games, but the board geometry is simpler.

## 6. Board Rendering

### `_refresh_board()`

Standard remove-and-rebuild pattern:

1. Remove existing children from board container
2. Append freshly built grid widget

### `_build_board_grid()`

Creates three rows:

1. Foundation row (4 piles)
2. Tableau top row (piles 1-6)
3. Tableau bottom row (piles 7-12)

Unlike Patience/FreeCell, Cruel uses named pile widgets for tableau columns because only top cards are interactive.

### Foundation/tableau pile builders

- `_build_foundation_pile(...)` uses explicit custom widget composition
- `_build_tableau_col(...)` delegates to shared `build_named_pile(...)`

This mixed approach is pragmatic: custom foundation click binding plus reusable tableau display.

## 7. Interaction Handlers

### New game

`_on_new_game_clicked(...)`:

1. Recreate state
2. Clear selection
3. Reset status
4. Refresh board

### Redeal

`_on_redeal_clicked(...)`:

1. Collect and redeal tableau
2. Clear selection
3. Check if any legal moves remain
4. If no moves: set game-over status and style
5. Otherwise refresh, compute auto foundation moves, animate them

### Foundation click

`_on_foundation_clicked(foundation_idx)`:

1. Requires a selected tableau source
2. Attempts top-card move to chosen foundation
3. On success: refresh + auto-move cascade + optional win check
4. On failure: set illegal move status

### Tableau click

`_on_tableau_clicked(pile_idx, _y_pos)`:

1. If same pile selected: deselect
2. If different pile selected: attempt move from selected pile top card
3. If no selection and pile non-empty: select its top card

`_y_pos` is accepted for API consistency but not used because Cruel never selects partial runs.

## 8. Auto-Move Animation and End State

### `_animate_auto_moves(...)`

Applies precomputed move list one step at a time with `GLib.timeout_add(440, ...)`.

Benefits:

1. Player can see progression to foundations
2. UI feels responsive and informative
3. Keeps deterministic order from `_collect_auto_moves`

### `_check_win()`

Sums foundation card counts and declares win at 52.

### `_set_status(...)`

Central status updater that also clears `game-over` CSS before applying new text.

## 9. Local CSS Layer

`_install_css()` defines:

- `.selected-pile`
- `.selected-card`
- `.game-over`

Theme layering model:

1. Global table/panel look comes from [src/patience/ui/theme.py](src/patience/ui/theme.py)
2. Cruel-specific interaction highlights are defined locally here

## 10. Launch Contract

`launch(parent_window)` at end of file:

1. Fetches application from parent
2. Raises clear error if missing
3. Creates `CruelWindow(app, parent)`
4. Calls `present()`

This is the exact interface expected by [src/patience/window.py](src/patience/window.py) when launching a game module dynamically.

## Why Cruel Is the Simplest Teaching Example

Compared to other game modules:

1. No stock/waste cycling logic
2. No multi-card run extraction from tableau
3. No free-cell capacity math
4. No reserve-specific mandatory movement logic
5. Still demonstrates full architecture from state to launch

That makes it ideal for understanding the baseline pattern before reading Patience, Demon, or FreeCell.

## Reading Checklist for This File

1. Start with `TABLEAU_COLS` and `PILE_SIZE` to lock board shape.
2. Read `create_initial_state()` to understand ace extraction + 12x4 tableau deal.
3. Read `can_place_on_foundation` and `can_place_on_tableau` to internalize legal moves.
4. Read `_on_tableau_clicked` and `_on_foundation_clicked` as the main interaction loop.
5. Read `_on_redeal_clicked` + `collect_and_redeal` to understand Cruel’s core mechanic.
6. Finish with `_animate_auto_moves` and `launch` to connect gameplay polish and app integration.

---

[Previous: generic game module pattern](game-module-pattern.md) | [Index](index.md) | [Next: Patience game deep dive](patience-game.py.md)
