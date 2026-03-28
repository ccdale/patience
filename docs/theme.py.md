[Previous: game registry notes](game-registry.md) | [Index](index.md) | [Next: help.py notes](help.py.md)

---

# Code Reading Notes: src/patience/ui/theme.py

## Purpose

This module installs global, app-level CSS for the card-table look and feel. It applies theme-aware styling for light and dark desktop modes and does it exactly once per app process.

The file solves three practical problems:

1. Avoid bright default GTK surfaces in light mode
2. Provide a darker, readable equivalent in dark mode
3. Ensure CSS provider installation is idempotent (no duplicate installs)

## Line-by-Line Reasoning

### Imports and GTK Version Guard

```python
import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

from gi.repository import Gdk, Gtk  # noqa: E402
```

- `gi` is PyGObject’s dynamic binding loader.
- `require_version` must run before importing from `gi.repository`.
- Both `Gdk` and `Gtk` are needed:
  - `Gdk` for display access (`Gdk.Display.get_default()`)
  - `Gtk` for CSS provider and style context APIs
- `# noqa: E402` is intentionally used here because imports must come after version guards.

### Module-Level Guard Flag

```python
_APP_THEME_CSS_INSTALLED = False
```

This is an idempotency guard. It prevents repeatedly adding the same CSS provider if `install_app_theme_css()` is called more than once.

Why this matters:

1. Multiple installs can stack style providers unnecessarily.
2. It keeps startup behavior predictable and cheap.
3. It makes calling code simpler because callers do not need to track install state.

## install_app_theme_css Function

```python
def install_app_theme_css() -> None:
    global _APP_THEME_CSS_INSTALLED
    if _APP_THEME_CSS_INSTALLED:
        return
```

### Early Return Guard

- Reads and updates module global via `global _APP_THEME_CSS_INSTALLED`.
- If already installed, exits immediately.
- This makes the function safe to call from startup paths without worrying about duplicates.

### Display Availability Check

```python
    display = Gdk.Display.get_default()
    if display is None:
        return
```

- Retrieves the active display object.
- If no display exists (for example, unusual headless or pre-display timing scenarios), it safely returns without error.

Design rationale: fail-soft behavior is better than crashing when display context is unavailable.

### CSS Provider Creation and Data Load

```python
    css = Gtk.CssProvider()
    css.load_from_data(
        b"""
        ... CSS ...
        """
    )
```

- Creates a `Gtk.CssProvider` instance.
- Loads CSS from a bytes literal (`b"""..."""`), which is what GTK expects.

This embeds app theme rules in one place, making them easy to version and ship with Python code without separate asset file handling.

## CSS Structure and Strategy

The CSS is split by media queries:

1. `@media (prefers-color-scheme: light)`
2. `@media (prefers-color-scheme: dark)`

That delegates theme mode detection to the desktop environment and GTK.

### Light Mode Block

Main selectors:

- `.table-window`
- `.table-window .pile-frame`
- `.table-window .rules-panel`
- `.table-window .rules-panel-header`
- `.table-window .rules-panel-icon`

Effects:

1. Applies a soft green vertical gradient to table backgrounds.
2. Uses translucent white-ish pile frames for layered card-table contrast.
3. Styles rules panel with lightly tinted background and subtle border.
4. Colors rules header/icon with a deeper green for clear readability.

Why it works: keeps the interface bright but not glaring while preserving the tabletop metaphor.

### Dark Mode Block

Uses the same selector set with darker palette values.

Effects:

1. Replaces light greens with deep forest tones in the table gradient.
2. Uses translucent dark pile frames with low-contrast green borders.
3. Keeps rules panel in the same tonal family to avoid bright patches.
4. Switches heading/icon to lighter green for contrast in dark contexts.

Why it works: visual consistency is maintained across modes because structure and selectors stay identical; only color values change.

## Provider Registration

```python
    Gtk.StyleContext.add_provider_for_display(
        display,
        css,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
    _APP_THEME_CSS_INSTALLED = True
```

- Registers the CSS provider on the active display.
- Uses `GTK_STYLE_PROVIDER_PRIORITY_APPLICATION` so app styles apply at application-level priority.
- Sets the installed flag only after successful registration.

Behavioral consequence: any widget with matching CSS classes receives these styles, regardless of which window constructs it.

## Mental Model

Think of this module as a one-time bootstrapped style layer:

1. App startup calls `install_app_theme_css()`.
2. Theme module checks whether CSS is already installed.
3. If not installed and display is available, it registers a single global provider.
4. Windows and widgets opt into styling by adding classes like `table-window`, `pile-frame`, and `rules-panel`.
5. Desktop light/dark preference selects the corresponding media block automatically.

This keeps theming centralized and avoids per-window CSS duplication.

## Architectural Patterns and Why They Work

### 1. Idempotent initializer

A public init function with a module-level guard is a clean pattern for setup code that should run once.

### 2. Class-based scoping

Using `.table-window` root class scopes styles to application windows that opt in, reducing accidental style bleed into unrelated widgets.

### 3. Shared selectors across color schemes

Both light and dark blocks style the same selector set. This minimizes drift and keeps layout/state appearance consistent while only colors vary.

### 4. Embedded CSS with GTK provider

Embedding CSS directly in module code keeps deployment simple for a Python app and makes style changes easy to audit in Git.

## Key Notes to Remember

1. `gi.require_version()` calls must stay before `from gi.repository import ...`.
2. `install_app_theme_css()` is safe to call multiple times because of `_APP_THEME_CSS_INSTALLED`.
3. If a window lacks `table-window` class, these background styles will not apply.
4. `pile-frame` and `rules-panel` styles depend on those classes being added in UI builder code.
5. Light/dark behavior is driven by desktop preference through `prefers-color-scheme`.
6. This module installs theme globally per display, not per window.
7. If future theme changes are needed, update both light and dark blocks in parallel to avoid visual mismatch.

---

[Previous: game registry notes](game-registry.md) | [Index](index.md) | [Next: help.py notes](help.py.md)
