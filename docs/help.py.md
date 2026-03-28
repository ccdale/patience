[Previous: theme.py notes](theme.py.md) | [Index](index.md) | [Next: cards.py notes](cards.py.md)

---

# Code Reading Notes: src/patience/ui/help.py

## Purpose

This module provides a shared, reusable builder for in-game rules/help UI. It encapsulates:

1. One-time CSS installation for rules-panel styling
2. Construction of a collapsible GTK rules widget
3. A simple API (`build_rules_panel`) used by multiple games

It exists to remove repeated UI code from each game module and keep help panel behavior visually consistent.

## Line-by-Line Reasoning

### Imports and GTK/GDK Version Guards

```python
import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

from gi.repository import Gdk, Gtk  # noqa: E402
```

- `gi.require_version(...)` must run before `from gi.repository import ...`.
- `Gdk` is required for display access when registering CSS provider.
- `Gtk` provides widgets and style APIs.
- `# noqa: E402` is intentional due to version-guard ordering.

### Module-Level CSS Guard

```python
_RULES_PANEL_CSS_INSTALLED = False
```

- Tracks whether panel CSS has already been registered.
- Prevents repeated provider registration when multiple game windows call `build_rules_panel()`.

This mirrors the app-level theme pattern: initialize once, then reuse.

## `_ensure_rules_panel_css()`

```python
def _ensure_rules_panel_css() -> None:
    global _RULES_PANEL_CSS_INSTALLED
    if _RULES_PANEL_CSS_INSTALLED:
        return
```

### Idempotency behavior

- Early-return if CSS is already installed.
- Keeps function safe to call every time a panel is built.

### Display retrieval and fail-soft behavior

```python
    display = Gdk.Display.get_default()
    if display is None:
        return
```

- If no display exists, function returns cleanly.
- This avoids crashes from trying to register styles without a display context.

### CSS provider creation

```python
    css = Gtk.CssProvider()
    css.load_from_data(
        b"""
        .rules-panel { ... }
        .rules-panel-header { ... }
        .rules-panel-body { ... }
        """
    )
```

Three class targets are defined:

1. `.rules-panel`
- Rounded corners and subtle border/background tint
- Provides a framed, card-like help container

2. `.rules-panel-header`
- Green, bold heading text
- Establishes visual hierarchy for panel title

3. `.rules-panel-body`
- Slightly softened text color via `alpha(currentColor, 0.92)`
- Keeps body text readable without hard contrast

### Provider registration

```python
    Gtk.StyleContext.add_provider_for_display(
        display,
        css,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
    _RULES_PANEL_CSS_INSTALLED = True
```

- Registers CSS at application priority for current display.
- Flag flips to `True` only after successful registration.

## `build_rules_panel(text, title="Rules")`

This is the public API of the module.

```python
def build_rules_panel(text: str, title: str = "Rules") -> Gtk.Widget:
    _ensure_rules_panel_css()
```

The first action ensures styles are available before any panel widget is built.

### Outer frame

```python
    frame = Gtk.Frame()
    frame.add_css_class("rules-panel")
```

- Frame acts as outer container.
- `rules-panel` class links this widget to installed CSS.

### Expander container

```python
    expander = Gtk.Expander()
    expander.set_expanded(False)
```

- Uses GTK expander for collapsible behavior.
- Starts collapsed by default to avoid crowding game layouts.

### Custom header composition

```python
    header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    ...
    icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic")
    icon.set_pixel_size(16)
    icon.add_css_class("rules-panel-icon")
    ...
    heading = Gtk.Label(label=title)
    heading.add_css_class("rules-panel-header")
    heading.set_halign(Gtk.Align.START)
    heading.set_xalign(0)
    ...
    expander.set_label_widget(header)
```

- Replaces plain expander label text with a richer custom header.
- Header contains icon + title for better affordance.
- Alignment calls (`set_halign`, `set_xalign`) pin label to left edge.

Note: `.rules-panel-icon` is styled by app theme module in table-window contexts, allowing dark/light adaptive icon color.

### Body container and text label

```python
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    ...
    help_text = Gtk.Label(label=text)
    help_text.add_css_class("rules-panel-body")
    help_text.set_wrap(True)
    help_text.set_halign(Gtk.Align.START)
    help_text.set_xalign(0)
    help_text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
```

- Vertical body box adds margins and spacing for readable content.
- Label wraps content and aligns to start.
- `WORD_CHAR` wrapping allows sensible breaks while still splitting long tokens when needed.

### Final assembly

```python
    box.append(help_text)
    expander.set_child(box)
    frame.set_child(expander)
    return frame
```

Returns a ready-to-embed GTK widget that callers can append to their layout.

## Mental Model

Think of this module as a mini component library entry:

1. `build_rules_panel()` is the only API callers need.
2. It lazily ensures CSS is installed once.
3. It returns a pre-assembled, collapsible panel with consistent styling.
4. Games only provide text/title content, not layout code.

That separation keeps game modules focused on game logic and interaction flow.

## Architectural Patterns and Why They Work

### 1. Reusable widget builder

A dedicated builder function for repeated UI avoids copy/paste drift across game modules.

### 2. Lazy one-time style installation

Installing CSS only when needed avoids startup coupling and repeated registration overhead.

### 3. Content vs presentation split

Games pass raw rule text while this module owns structure and styling.

### 4. Theme layering compatibility

Local CSS sets baseline rules panel style; app-level theme selectors can refine colors by light/dark mode when inside `.table-window`.

## Key Notes to Remember

1. `build_rules_panel()` is the stable integration point for game modules.
2. Panel starts collapsed by default (`set_expanded(False)`).
3. `.rules-panel-icon` relies on broader theme styles for final color in themed windows.
4. `_RULES_PANEL_CSS_INSTALLED` prevents duplicate provider registration.
5. The returned type is `Gtk.Widget`, allowing flexible placement in any GTK container.
6. The helper accepts plain strings, so callers can generate dynamic rules text if needed.
7. This file intentionally contains no game-specific knowledge.

---

[Previous: theme.py notes](theme.py.md) | [Index](index.md) | [Next: cards.py notes](cards.py.md)
