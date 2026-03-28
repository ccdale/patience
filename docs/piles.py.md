[Previous: cards.py notes](cards.py.md) | [Index](index.md) | [Next: generic game module pattern](game-module-pattern.md)

---

# Code Reading Notes: src/patience/ui/piles.py

## Purpose

This module contains reusable GTK builders for pile-shaped UI blocks used across multiple games. It provides two primary widgets:

1. A compact named pile widget for stock, waste, foundation, reserve-like piles
2. A stacked tableau-column widget with card overlap and click-position handling

It centralizes visual and interaction behavior so game modules do not repeat the same layout code.

## Line-by-Line Reasoning

### Imports and Constants

```python
from collections.abc import Callable

import gi
from ccacards.card import Card
from ccacards.pile import Pile

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk  # noqa: E402

from patience.ui.cards import CARD_H, CARD_W  # noqa: E402
```

- `Callable` is used to type callback and card-rendering hooks.
- `Card` and `Pile` are data primitives from ccacards.
- GTK import order follows the standard version-guard pattern.
- `CARD_W` and `CARD_H` are imported from the card widget module, keeping dimensions consistent across UI components.

Spacing constants:

```python
TABLEAU_COL_GAP = 14
FACE_DOWN_OVERLAP = 22
FACE_UP_OVERLAP = 38
```

- `TABLEAU_COL_GAP` represents intended horizontal spacing between columns (used by callers/layouts).
- Overlap constants control how much of each card remains visible in a vertical stack.
- Face-up cards reveal more than face-down cards, improving readability of playable runs.

## build_named_pile

```python
def build_named_pile(
    title: str,
    pile: Pile,
    card_builder: Callable[[Card | None], Gtk.Widget],
    on_click: Callable[[], None] | None = None,
    selected: bool = False,
) -> Gtk.Widget:
```

### API contract

- `title`: text label shown above the pile preview.
- `pile`: source pile to display top card and card count.
- `card_builder`: injected renderer for a card slot, allowing this module to stay independent of concrete card image logic.
- `on_click`: optional click handler for interactions.
- `selected`: optional visual selection state.

### Widget composition

1. Creates a `Gtk.Frame` with fixed card width and class `pile-frame`.
2. Adds `selected-pile` class when selected for highlight styling.
3. Creates inner vertical box with margins.
4. Appends title label.
5. Appends rendered top-card widget from `card_builder(pile.peek())`.
6. Appends count label showing total cards.
7. Installs optional click gesture on the frame.

Design notes:

- `card_builder` decouples this module from resource-path/image specifics.
- Displaying both top card and count gives useful info even when top card is hidden/empty.
- Gesture is attached only when callback exists, keeping passive widgets lightweight.

### Click handling pattern

```python
click = Gtk.GestureClick.new()
click.connect("released", lambda *_args: on_click())
frame.add_controller(click)
```

- Uses release event instead of press, matching common GTK button-like interaction behavior.
- Lambda ignores gesture parameters and calls simple zero-argument callback.

## build_tableau_column

```python
def build_tableau_column(
    index: int,
    pile: Pile,
    card_builder: Callable[[Card | None], Gtk.Widget],
    on_click: Callable[[float], None] | None = None,
    selected_start_index: int | None = None,
) -> Gtk.Widget:
```

### API contract

- `index`: displayed as T1, T2, etc.
- `pile`: tableau pile to render.
- `card_builder`: card widget factory.
- `on_click`: optional callback receiving Y coordinate in the card stack area.
- `selected_start_index`: start of selected run within pile, used for range highlighting.

### Structure

1. Outer frame with `pile-frame` class.
2. Optional `selected-pile` class when a run is selected.
3. Vertical outer box with caption label `T{index}`.
4. `Gtk.Fixed` container for pixel-positioned card stack.

Why `Gtk.Fixed` is used:

- Tableau stacking needs precise Y offsets per card.
- Standard box layouts cannot express overlapping children cleanly.

### Card placement algorithm

Core loop:

```python
y = 0
for i, card in enumerate(cards):
    widget = card_builder(card)
    if selected_start_index is not None and i >= selected_start_index:
        widget.add_css_class("selected-card")
    fixed.put(widget, 0, y)
    if i < len(cards) - 1:
        y += FACE_DOWN_OVERLAP if card.facedown else FACE_UP_OVERLAP
```

Behavior:

1. Start at Y=0 for first card.
2. Place each card at current Y.
3. Increment Y by smaller overlap for face-down cards, larger overlap for face-up cards.
4. Highlight selected tail of run with `selected-card` class.

Result: a natural tableau fan where hidden cards are compact and face-up runs are more legible.

### Height calculation

```python
total_height = y + CARD_H
fixed.set_size_request(CARD_W, total_height)
```

- Ensures container height includes last card full height.
- Prevents clipping and keeps hitbox aligned with rendered stack.

### Position-aware click callback

```python
click.connect("released", lambda _gesture, _n_press, _x, y_pos: on_click(y_pos))
```

- Callback receives stack-local Y coordinate.
- Caller can convert click Y to card index to select partial runs.
- This is key for games that support moving a subset of a tableau pile.

## Mental Model

Think of this module as a visual adapter between ccacards piles and GTK widgets:

1. Game modules own state and move rules.
2. This module owns pile presentation and interaction surface.
3. Games provide renderer and callbacks.
4. This module returns ready-to-insert GTK widgets with shared styling classes.

That keeps game windows focused on behavior rather than repetitive widget plumbing.

## Architectural Patterns and Why They Work

### 1. Dependency injection via card_builder

Injecting the card renderer prevents tight coupling and makes pile builders reusable for any card appearance strategy.

### 2. Event callback injection

Callbacks are optional and caller-provided, so the same widget can be static (display-only) or interactive.

### 3. CSS class-based state expression

Selection state is represented by classes (`selected-pile`, `selected-card`) rather than manual style properties, allowing theme modules to control visuals.

### 4. Pixel layout only where necessary

Most layout uses standard GTK boxes; only tableau cards use fixed positioning where overlap logic demands precision.

## Key Notes to Remember

1. `build_named_pile` is for top-card preview and count display.
2. `build_tableau_column` is for overlapping card stacks with position-aware clicks.
3. Face-up and face-down overlap values intentionally differ for readability.
4. `selected_start_index` highlights from a point to the end of pile, supporting run selection UX.
5. Height computation must include full card height to avoid clipping.
6. This module depends on card dimensions from the card widget module for consistency.
7. CSS classes require theme support to produce visible highlights.

---

[Previous: cards.py notes](cards.py.md) | [Index](index.md) | [Next: generic game module pattern](game-module-pattern.md)
