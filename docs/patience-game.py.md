[Previous: Cruel game deep dive](cruel-game.py.md) | [Index](index.md) | [Next: index](index.md)

---

# Code Reading Notes: src/patience/games/patience/game.py

## Purpose

This module implements classic Patience/Klondike gameplay with draw-3 stock, waste pile, 7-column tableau, and auto-foundation behavior.

Compared with Cruel, this module adds complexity in three places:

1. Stock/waste cycling (draw and redeal)
2. Partial tableau-run selection and movement
3. Face-down card reveal logic after moves

It still follows the same architecture described in [docs/game-module-pattern.md](docs/game-module-pattern.md).

## How It Maps to the Generic Pattern

The file follows the common order:

1. Imports and constants
2. State and selection dataclasses
3. Pure rule/helper functions
4. Initial state/deal construction
5. Window class (build UI, react to input)
6. Launch entry point

## 1. Imports and Constants

At [src/patience/games/patience/game.py](src/patience/games/patience/game.py):

- Uses `Card`, `Pack`, and `Pile` from ccacards
- Uses `gi.require_version` before GTK imports
- Uses shared UI helpers from cards/help/piles modules

Key constant:

- `DRAW_COUNT = 3`

This drives stock-click behavior (draw three cards to waste).

## 2. State and Selection

### `PatienceState`

```python
@dataclass(frozen=True)
class PatienceState:
    stock: Pile
    waste: Pile
    foundations: tuple[Pile, Pile, Pile, Pile]
    tableau: tuple[Pile, Pile, Pile, Pile, Pile, Pile, Pile]
```

State topology is the classic Klondike board:

1. One stock
2. One waste
3. Four foundations
4. Seven tableau piles

### `Selection`

```python
@dataclass
class Selection:
    source: str  # "waste", "foundation", "tableau"
    pile_index: int
    start_index: int | None = None
```

Why `start_index` matters here:

- Patience supports moving a run from inside a tableau column.
- `start_index` marks where the selected run begins.

## 3. Rule Functions (Pure Logic)

### Color helper

`is_red(card)` centralizes suit color logic.

### Foundation placement

`can_place_on_foundation(card, foundation_top)`:

1. Empty foundation accepts Ace only.
2. Otherwise same suit + ascending by one.

### Tableau placement

`can_place_on_tableau(card, tableau_top)`:

1. Empty tableau accepts King only.
2. Otherwise alternating color + descending by one.

### Tableau-run validation

`is_valid_tableau_run(cards)` ensures:

1. Run is non-empty
2. No card is face-down
3. Adjacent cards alternate color and descend by one

### Stock/waste helpers

- `draw_three_from_stock(...)`
- `redeal_waste_to_stock(...)`

These are pure move primitives used by stock-click logic.

## 4. Initial Deal (`create_initial_state`)

This function builds the opening layout:

1. Shuffle pack
2. Create empty foundations, tableau, stock, waste
3. Deal tableau columns 1..7 cards each
4. Keep only top tableau card face-up in each column
5. Move remaining cards into stock face-down

Key detail:

- During tableau dealing, all cards except each column’s top are flipped facedown.
- Stock cards are normalized to facedown.

This exactly encodes standard Klondike initial orientation.

## 5. Window Constructor and Layout

`PatienceWindow` constructor in [src/patience/games/patience/game.py](src/patience/games/patience/game.py):

1. Sets title/size and adds `table-window` CSS class
2. Sets transient parent if launched from launcher
3. Initializes `_state`, `_selection`, `_card_data_dir`
4. Installs selection CSS
5. Builds root with:
- header (title + New Game)
- status label
- rules panel
- board container
6. Calls `_refresh_board()` and sets root child

This is the same overall UI flow as other games.

## 6. Board Rendering

### `_refresh_board()`

Uses remove-and-rebuild pattern:

1. Remove old child widgets from board container
2. Append newly built grid from current state

### `_build_board_grid()`

Builds a 7-column grid with two rows:

- Top row: Stock, Waste, gap, Foundation 1..4
- Bottom row: Tableau columns 1..7

The method uses shared builders:

1. `build_named_pile` for stock/waste/foundations
2. `build_tableau_column` for tableau stacks

Selection state is wired into the builders via:

- `_is_selected_named(...)`
- `_selected_tableau_start(...)`

So selection highlighting is purely data-driven.

## 7. Selection Model

Patience supports selecting from three sources:

1. Waste top card
2. Foundation top card
3. Tableau top card or tableau run

Selection helpers:

- `_is_selected_named(...)`: checks selected named pile
- `_selected_tableau_start(...)`: returns selected run start for one tableau column

This keeps UI highlight logic centralized and prevents duplicated condition checks.

## 8. Event Handlers

### New game

`_on_new_game_clicked(...)`:

1. Reset state via `create_initial_state()`
2. Clear selection
3. Reset status
4. Refresh board

### Stock click

`_on_stock_clicked()`:

1. Try draw-3 from stock
2. If stock empty, try redeal waste -> stock
3. On any change: clear selection, run auto-foundation, refresh board

### Waste click

`_on_waste_clicked()`:

1. If waste empty: clear selection
2. If already selected waste: deselect
3. Else: select waste top card

### Foundation click

`_on_foundation_clicked(foundation_idx)` has dual behavior:

1. If something is selected: attempt move selection -> clicked foundation
2. If nothing selected: select top card of clicked foundation

### Tableau click

`_on_tableau_clicked(tableau_idx, y_pos)`:

1. Compute clicked card index from Y position
2. If a selection already exists: try move selection -> clicked tableau
3. If clicked facedown top card: flip it
4. Else select top card or run starting at clicked face-up index

This is where Patience gets much richer than Cruel because click position can select internal run segments.

## 9. Move Execution Helpers

### `_move_selection_to_foundation(...)`

Validation path:

1. Ensure there is a selected source
2. Peek selected lead card
3. Validate foundation placement rule
4. Enforce single-card-only move to foundation
5. Pop selected card(s), append to destination, cleanup source

### `_move_selection_to_tableau(...)`

Validation path:

1. Block same-tableau destination
2. Get selected cards
3. Validate selected run
4. Validate destination tableau rule
5. Pop and append moved cards in order
6. Cleanup source (flip revealed facedown top if needed)

### Shared card extraction helpers

- `_peek_selected_card`
- `_selection_is_single_card`
- `_get_selected_cards`
- `_pop_selected_cards`
- `_post_source_cleanup`

These helpers isolate source-specific logic (`waste` vs `foundation` vs `tableau`) and reduce branching in click handlers.

## 10. Auto-Foundation Loop

`_auto_move_to_foundations()` repeatedly applies obvious foundation moves until no more exist.

Loop behavior:

1. Try waste top to foundations first
2. Then try each tableau top (face-up only)
3. After moving from tableau, flip newly exposed facedown top card
4. Continue until no move occurs in a pass

This is a deterministic cascade that simplifies gameplay and reduces repetitive manual clicks.

## 11. Tableau Click Geometry

`_tableau_card_index_from_y(pile, y_pos)` maps click Y coordinate to a card index.

How it works:

1. Build a list of card start Y positions using overlap values
2. Scan from topmost visual card backward
3. Return first start <= clicked Y

Why this matters:

- Correct run selection depends on precise hit-testing in stacked cards.
- It mirrors the visual layout used by shared tableau builder.

## 12. Styling Layer

`_install_selection_css()` defines local classes:

1. `.selected-pile`
2. `.selected-card`

Global theme still comes from [src/patience/ui/theme.py](src/patience/ui/theme.py); this local CSS only controls interactive highlights.

## 13. Launch Contract

`launch(parent_window)`:

1. Reads parent’s GTK application
2. Raises clear runtime error if missing
3. Creates `PatienceWindow(app, parent)`
4. Presents window

This matches launcher expectations from [src/patience/window.py](src/patience/window.py).

## Patience vs Cruel: Quick Contrast

Why Patience is a next step after Cruel:

1. Adds stock/waste state transitions
2. Adds run selection and movement
3. Adds click-position to card-index mapping
4. Adds automatic foundation cascade from both waste and tableau

What remains familiar:

1. Same module skeleton and launch contract
2. Same state + rules + window layering
3. Same remove/rebuild board rendering pattern
4. Same shared UI helper usage

## Reading Checklist

1. Read `create_initial_state()` to lock in stock/waste/tableau orientation logic.
2. Read `can_place_on_*` plus `is_valid_tableau_run` to internalize legal moves.
3. Read `_on_stock_clicked`, `_on_waste_clicked`, `_on_tableau_clicked` for interaction flow.
4. Read `_get_selected_cards` and `_pop_selected_cards` to understand source-dependent extraction.
5. Read `_auto_move_to_foundations` to understand automatic cascade side effects.
6. Read `_tableau_card_index_from_y` for run-hit-testing mechanics.

---

[Previous: Cruel game deep dive](cruel-game.py.md) | [Index](index.md) | [Next: index](index.md)
