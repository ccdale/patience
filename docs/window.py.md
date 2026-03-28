[Previous: app.py notes](app.py.md) | [Index](index.md) | [Next: game registry notes](game-registry.md)

---

# Code Reading Notes: src/patience/window.py

## Purpose

`window.py` defines `LauncherWindow`, the main user-facing window that appears when the application starts. It shows available solitaire games as clickable tiles in a 3-column grid and handles the dynamic launch of selected games. This is the "menu" screen that users interact with before choosing which game to play.

## Line-by-Line Reasoning

### Imports (Lines 1–10)

```python
import importlib
from importlib import resources

import gi

from patience.games.registry import GAME_ICON_FILENAME, GAME_REGISTRY, GameSpec

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk  # noqa: E402
```

**Why these imports?**
- `importlib`: Standard library for dynamic module importing. Allows code to load Python modules at runtime (e.g., `importlib.import_module("patience.games.freecell")`).
- `importlib.resources`: Standard library for accessing bundled package resources (e.g., SVG icons stored inside game packages).
- `gi` and `Gtk`: GTK framework for GUI widgets and window management.
- `GAME_REGISTRY`: The tuple of `GameSpec` entries from registry.py; defines what games are available and their metadata.
- `GAME_ICON_FILENAME` and `GameSpec`: Constants and dataclass from registry.py used for game discovery.

**Import order note:** `gi.require_version()` must come before GTK imports, so the GTK import has `# noqa: E402` to suppress the linter warning about imports not being at the top.

---

## LauncherWindow Class Design

### Constructor (`__init__`, Lines 13–47)

```python
class LauncherWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application) -> None:
        super().__init__(application=app)
        self.set_title("Patience")
        self.set_default_size(840, 560)
        self.add_css_class("table-window")
        
        # ... widget setup code ...
```

**Constructor responsibilities:**
1. **Window initialization:** Inherits from `Gtk.ApplicationWindow`, which ties the window to the GTK Application lifecycle. The `application=app` parameter registers this window with the app so GTK can manage it properly.
2. **Window properties:** Title set to "Patience" (appears in taskbar/title bar). Default size 840×560 gives enough space for a 3-column grid of game tiles.
3. **Theming:** `add_css_class("table-window")` applies the green card-table background and styling defined in `src/patience/ui/theme.py`.

**Widget hierarchy strategy:**
The window contains a vertical `Gtk.Box` with:
1. **Title section** (lines 24–34): "Choose A Solitaire Game" heading and instructional text.
2. **Grid section** (lines 36–47): 3-column grid of game tiles, one tile per game in `GAME_REGISTRY`.

**Grid layout logic (lines 42–45):**
```python
max_columns = 3
for index, game in enumerate(GAME_REGISTRY):
    row = index // max_columns      # 0,0,0,1,1,1,2,2,2 for 9 games
    column = index % max_columns    # 0,1,2,0,1,2,0,1,2 for 9 games
    grid.attach(self._build_game_tile(game), column, row, 1, 1)
```
This calculates grid position from a flat index. For index 5: `row = 5 // 3 = 1`, `column = 5 % 3 = 2`, placing it at row 1, column 2 (bottom-right of first 3×2 block).

---

## The `_build_game_tile` Method (Lines 49–84)

This method builds a single game tile (card-like frame showing game icon, title, module name, and launch button).

**Widget structure:**
- **Frame (outer):** Container that gives the tile a border/background.
  - **Box (vertical, inner):** Holds the content with 10px spacing between sections.
    - **Header (horizontal):** Game icon on left, title+module labels on right.
      - **Icon (Gtk.Image):** 48×48 pixel game icon.
      - **Labels (vertical):** Game title and module name stacked.
    - **Spacer (empty Box with vexpand=True):** Pushes launch button to bottom.
    - **Launch button:** Clickable button to start the game.

**Key detail:** The header is horizontal with the icon on the left and labels taking up remaining space (`labels.set_hexpand(True)`). The spacer box below the header (with `vexpand=True`) forces the launch button to the bottom of the tile, creating a consistent bottom-aligned button layout regardless of title length.

**Button state:** `launch.set_sensitive(game.available)` disables the button if the game is marked `available=False` in the registry. Disabled buttons are greyed out and non-clickable.

**Button callback:** `launch.connect("clicked", self._on_launch_clicked, game)` wires the button click to `_on_launch_clicked`, passing the game spec as a parameter.

---

## The `_build_game_icon` Method (Lines 86–94)

```python
def _build_game_icon(self, game: GameSpec) -> Gtk.Image:
    icon_path = self._find_game_icon_path(game)
    if icon_path is not None:
        icon = Gtk.Image.new_from_file(icon_path)
    else:
        icon = Gtk.Image.new_from_icon_name("applications-games-symbolic")
    icon.set_pixel_size(48)
    icon.set_halign(Gtk.Align.START)
    icon.set_valign(Gtk.Align.START)
    return icon
```

**Purpose:** Creates a GTK Image widget for a game, either from the game's custom SVG icon or a fallback symbolic icon if the custom icon is not found.

**Fallback strategy:** If `_find_game_icon_path` returns `None` (icon file not found or module not available), use GTK's built-in `"applications-games-symbolic"` icon. This ensures the UI never breaks due to missing assets.

**Sizing:** `set_pixel_size(48)` makes the icon 48×48 pixels. For PNG/JPEG this is fixed; for SVG it scales the vector to that size.

**Alignment:** `START` aligns icon to top-left of its cell, which looks natural in the header layout.

---

## The `_find_game_icon_path` Method (Lines 96–105)

```python
def _find_game_icon_path(self, game: GameSpec) -> str | None:
    try:
        icon_resource = resources.files(game.module).joinpath(GAME_ICON_FILENAME)
    except (ModuleNotFoundError, TypeError):
        return None
    if not icon_resource.is_file():
        return None
    return str(icon_resource)
```

**Purpose:** Safely locate a game's icon file without requiring manual path construction.

**How it works:**
1. `resources.files(game.module)` - Get a reference to the game package (e.g., `"patience.games.freecell"`).
2. `.joinpath(GAME_ICON_FILENAME)` - Navigate to the icon file inside that package (e.g., `"game-icon.svg"`).
3. `.is_file()` - Verify the resource exists and is a file (not a directory).
4. `str(...)` - Convert the resource reference to a filesystem path string usable by GTK.

**Error handling:** Catches both `ModuleNotFoundError` (game package not found) and `TypeError` (if something goes wrong with the resource API). Returns `None` on any error, allowing the caller to fall back to a default icon.

**Why this approach?** Using `importlib.resources` is the standard way to access bundled assets in Python packages. It works whether the package is installed normally, in development mode, or even inside a ZIP file. Constructing ad-hoc file paths would be fragile.

---

## The `_on_launch_clicked` Method (Lines 107–124)

This is the core game-launching logic triggered when a user clicks a game tile's launch button.

```python
def _on_launch_clicked(self, _button: Gtk.Button, game: GameSpec) -> None:
    if not game.available:
        self._show_info_dialog(f"{game.title} is not wired yet.")
        return

    try:
        game_module = importlib.import_module(game.module)
    except Exception as exc:
        self._show_info_dialog(f"Could not import {game.module}: {exc}")
        return

    launch = getattr(game_module, "launch", None)
    if not callable(launch):
        self._show_info_dialog(
            f"{game.module} does not define launch(parent_window)."
        )
        return

    launch(self)
```

**Step-by-step:**

1. **Check availability** (line 109): If the game is marked `available=False`, show a friendly message ("is not wired yet") and exit. This allows marking games as "coming soon" without showing them as broken.

2. **Import the game module** (line 113): `importlib.import_module(game.module)` dynamically loads the game package at runtime. For example, if `game.module = "patience.games.freecell"`, this loads that module into memory.

3. **Error handling on import** (line 114–115): If import fails (syntax error, missing dependency, etc.), catch the exception and show the error message to the user.

4. **Find the `launch` function** (line 118): Every game module must export a `launch(parent_window)` function (the convention established by the codebase). `getattr` retrieves it or returns `None` if not found.

5. **Validate the function** (line 119–123): If `launch` is not found or is not callable, show an error dialog explaining what went wrong.

6. **Call the game** (line 125): If all checks pass, call `launch(self)`. The game window is responsible for creating itself and presenting to the user. The launcher passes `self` (the LauncherWindow) as the parent, so the game window is modal to the launcher.

**Design insight:** This is a flexible plugin pattern. Games are discovered via the registry (which games exist), but the launcher doesn't need to know anything about game internals. It just loads the module and calls the agreed-upon `launch()` function. New games can be added by registering them and ensuring they export `launch()`.

---

## The `_show_info_dialog` Method (Lines 126–133)

```python
def _show_info_dialog(self, text: str) -> None:
    dialog = Gtk.MessageDialog(
        transient_for=self,
        modal=True,
        buttons=Gtk.ButtonsType.OK,
        text=text,
    )
    dialog.connect("response", lambda d, _r: d.close())
    dialog.present()
```

**Purpose:** Show an informational popup dialog (error message, warning, etc.).

**Modal window:** `transient_for=self` makes this dialog modal relative to the launcher window—the user cannot interact with the launcher until dismissing the dialog. `modal=True` reinforces this.

**Button setup:** `buttons=Gtk.ButtonsType.OK` adds an OK button. No other action buttons.

**Auto-dismiss:** The dialog is set up to close itself when the user responds: `dialog.connect("response", lambda d, _r: d.close())`. The lambda takes the dialog `d` and the response code `_r` (ignored), and closes the dialog.

**No return value:** The method doesn't return anything or wait for a response. It just shows the dialog and returns. GTK's event loop handles user interaction asynchronously.

---

## Mental Model: How It All Fits Together

Think of `LauncherWindow` as the **game selector menu**. When the app starts (via `app.py`), the launcher window is created and shown. The user sees a grid of game tiles. When they click "Launch" on a tile:

1. The launcher looks up the game's metadata in the registry (title, module name, whether it's available).
2. The launcher dynamically imports the game module at runtime.
3. The launcher calls the game's `launch()` function, passing itself as the parent.
4. The game module creates its own window (as a child of the launcher) and shows it.
5. The game window runs its own event loop, handling game logic and user interaction.
6. When the user closes the game window, control returns to the launcher.

The launcher is intentionally **dumb**—it doesn't know how to play any game, how to draw cards, or how to validate moves. It's just a gateway that knows how to find, validate, and launch game modules. This separation makes it easy to add new games without touching the launcher code.

---

## Key Architectural Patterns

### 1. **Widget Hierarchy is Clean and Readable**
The nested Box structure makes the layout self-explanatory:
- Vertical box contains title section + grid.
- Grid contains tile frames.
- Each tile frame contains header (icon + labels) + spacer + button.

Understanding the layout requires reading the constructor once; no need to trace through complex CSS or dynamic calculations.

### 2. **Error Handling is User-Friendly**
Every fallible operation (finding icon, importing module, getting `launch` function) has a clear error path with a user-facing message. The app never crashes silently; it tells the user what went wrong.

### 3. **Dynamic Module Loading is an Explicit Convention**
Games are plugins loaded at runtime via `importlib.import_module()`. The contract is simple: if a game is in the registry and available, it must export a `launch(parent_window)` function. This is enforced in the test suite (`test_registry.py`).

### 4. **Fallback Icons Prevent Broken UI**
If a game's icon is missing, the launcher uses a stock GTK icon instead of showing a broken image or crashing. This is graceful degradation.

### 5. **The Registry is the Single Source of Truth**
All game metadata comes from `GAME_REGISTRY`. Want to add a game? Register it. Want to hide a game? Mark `available=False`. Want to rename a game? Update the registry entry. The launcher code doesn't need to change.

---

## Key Notes to Remember

1. **LauncherWindow is a Gtk.ApplicationWindow**, not a Gtk.Window. This ties it to the GTK Application lifecycle so it's managed by the app (close the launcher to close the app, etc.).

2. **The 3-column grid layout** uses modulo arithmetic (`index % max_columns` for column, `index // max_columns` for row). Easy to change to 2 or 4 columns: just change `max_columns`.

3. **The `_find_game_icon_path()` method uses `importlib.resources`**, which is the proper way to access bundled package assets (not ad-hoc `__file__` path manipulation). This works regardless of how Python finds the package (normal install, editable install, ZIP, etc.).

4. **Error handling is multi-layered:** Check availability → import module → find launch function → call it. Each layer has its own error dialog so the user knows exactly what went wrong.

5. **The game launch pattern is a plugin architecture:** Registry says "this game exists", launcher verifies the module can be imported and `launch()` exists, then calls it. Games are independent; launcher doesn't need to know their internal structure.

6. **Icon display has a fallback:** If the custom icon file is not found, GTK's built-in "applications-games-symbolic" icon is used. This prevents broken UI due to missing assets.

7. **The spacer Box with `vexpand=True`** is a common GTK pattern for bottom-aligning a widget within a container. The spacer takes up all extra vertical space, pushing the button to the bottom of the tile.

8. **Modal dialogs** created by `_show_info_dialog()` freeze interaction with the launcher until dismissed. `lambda d, _r: d.close()` is a standard pattern for auto-closing dialogs.

9. **The launcher doesn't know about game rules or UI.** It only knows how to find, validate, and launch game modules. This keeps the launcher code thin and game-agnostic.

10. **Adding a new game requires:** (1) Create game package under `src/patience/games/`, (2) Implement `launch(parent_window)` function, (3) Add a `game-icon.svg` file, (4) Register the game in `GAME_REGISTRY`. The launcher picks it up automatically.

---

[Previous: app.py notes](app.py.md) | [Index](index.md) | [Next: game registry notes](game-registry.md)
