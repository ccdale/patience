[Previous: help.py notes](help.py.md) | [Index](index.md) | [Next: piles.py notes](piles.py.md)

---

# Code Reading Notes: src/patience/ui/cards.py

## Purpose

This module provides card-level rendering helpers and shared card dimensions. It translates a card model object into a GTK widget by resolving the correct image path, with a graceful fallback when images are unavailable.

It defines:

1. Canonical card dimensions
2. Card asset directory resolution
3. Card-face/back/empty image path selection
4. GTK widget construction for card display

## Line-by-Line Reasoning

### Imports and Version Guard

```python
from pathlib import Path

import gi
from ccacards.card import Card

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk  # noqa: E402
```

- `Path` is used for file path operations in a platform-safe way.
- `Card` from ccacards provides card data and image metadata.
- GTK import follows required order after version guard.

### Shared Dimensions

```python
CARD_W = 90
CARD_H = 126  # proportional to natural 537×750 px
```

- These constants define the visual card size across the app.
- Ratio follows original source image aspect.
- Centralizing size constants keeps all piles/tableaus aligned and predictable.

## resolve_card_data_dir

```python
def resolve_card_data_dir() -> Path:
    return Path(Card(1).imagefile).parent
```

Purpose:

- Finds the directory where card image assets live by inspecting a known card image path from the ccacards library.

Why this is useful:

1. Avoids hard-coded absolute paths.
2. Adapts automatically to environment/package location.
3. Lets callers pass one directory to repeated rendering calls.

Implementation nuance:

- Creates `Card(1)` as a simple way to obtain a valid imagefile path anchor.

## resolve_card_image_path

```python
def resolve_card_image_path(card: Card | None, card_data_dir: Path) -> Path | None:
    if card is None:
        image_path = card_data_dir / "0.png"
    elif card.facedown:
        image_path = card_data_dir / "back.png"
    else:
        image_path = card.imagefile

    return image_path if image_path.is_file() else None
```

This function decides which image should represent a card slot.

Cases:

1. `card is None`
- Uses empty-slot image `0.png`
- Represents blank pile position

2. `card.facedown`
- Uses shared card back image `back.png`

3. Otherwise
- Uses the specific card face image from `card.imagefile`

Safety step:

- Verifies file existence with `is_file()`.
- Returns `None` if missing, enabling fallback rendering.

Design benefit: this function isolates asset-selection logic from widget construction.

## build_card_widget

```python
def build_card_widget(card: Card | None, card_data_dir: Path) -> Gtk.Widget:
    image_path = resolve_card_image_path(card, card_data_dir)
    if image_path is not None:
        picture = Gtk.Picture.new_for_filename(str(image_path))
        picture.set_size_request(CARD_W, CARD_H)
        picture.set_content_fit(Gtk.ContentFit.FILL)
        return picture

    fallback = Gtk.Box()
    fallback.set_size_request(CARD_W, CARD_H)
    fallback.add_css_class("card")
    fallback.add_css_class("frame")
    label = Gtk.Label(label="Empty" if card is None else str(card))
    label.set_wrap(True)
    fallback.append(label)
    return fallback
```

### Primary path (image available)

- Builds `Gtk.Picture` from filename.
- Applies canonical card size.
- Uses content fit fill so image occupies card bounds.

### Fallback path (image missing)

- Builds a framed box with same dimensions.
- Adds a text label:
  - Empty for no card
  - String representation for a concrete card

Why fallback matters:

1. Prevents hard failure when assets are missing.
2. Keeps game functional and debuggable even in partial environments.
3. Preserves layout dimensions, avoiding UI collapse.

## Mental Model

This module is the lowest UI layer for card visuals:

1. Determine where card assets live.
2. Choose the right image path for current card state.
3. Return a GTK widget of standard size.
4. Fall back to a text-based placeholder when image loading is impossible.

Higher-level modules like pile/tableau builders consume this API rather than dealing with file logic directly.

## Architectural Patterns and Why They Work

### 1. Separation of concerns

Path resolution, path selection, and widget creation are split into focused functions.

### 2. Canonical sizing constants

Single source for card dimensions prevents drift across UI modules.

### 3. Fail-soft rendering

Returning a valid fallback widget instead of throwing keeps UX stable under missing assets.

### 4. Pathlib-first path logic

Using `Path` keeps path operations explicit and cross-platform robust.

## Key Notes to Remember

1. `CARD_W` and `CARD_H` are shared dimensions used by other UI modules.
2. `resolve_card_data_dir()` discovers asset directory dynamically from ccacards.
3. `resolve_card_image_path()` handles empty, facedown, and face-up cases.
4. File existence is checked before rendering image widgets.
5. `build_card_widget()` always returns a valid GTK widget, image or fallback.
6. Fallback widgets keep layout intact while surfacing asset problems visibly.
7. This module is intentionally generic and game-agnostic.

---

[Previous: help.py notes](help.py.md) | [Index](index.md) | [Next: piles.py notes](piles.py.md)
