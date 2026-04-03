[Previous: index](index.md) | [Index](index.md) | [Next: window.py notes](window.py.md)

---

**Purpose**

This file is the application entry point. Its job is intentionally small:
1. tell PyGObject which GTK version to use
2. define the top-level `Gtk.Application`
3. create or reuse the main launcher window when the app activates
4. start the GTK event loop from `main()`

**Line-by-line reasoning**

`import gi`
This brings in PyGObject, which is the Python bridge to GTK.

`gi.require_version("Gtk", "4.0")`
This forces the process to bind against GTK 4, not some other installed GTK version. It has to happen before importing `Gtk` from `gi.repository`, otherwise the binding decision may already be made.

`from gi.repository import Gtk`
This imports the GTK API after the version has been locked in.

`from patience.ui.theme import install_app_theme_css`
This pulls in the shared app-level CSS installer. The reasoning is that theme setup should happen once at startup, not separately in every window.

`from patience.window import LauncherWindow`
This imports the main launcher window class. app.py does not build UI itself; it delegates that to a dedicated window module.

**`PatienceApplication`**

`class PatienceApplication(Gtk.Application):`
GTK applications are usually structured around a `Gtk.Application`, not just loose windows. This gives lifecycle hooks, application identity, window tracking, and integration with the desktop environment.

`super().__init__(application_id="org.cca.patience")`
The `application_id` is the app’s stable desktop identifier. It matters for desktop integration and for GTK’s application model. It also helps GTK understand whether windows belong to the same app instance.

**`do_activate`**

`def do_activate(self) -> None:`
This is the GTK activation hook. GTK calls it when the app is launched or re-activated.

The `# noqa: N802` comment:
GTK virtual methods use names like `do_activate`, which do not follow normal Python naming lint expectations for overridden framework methods. The comment suppresses that warning rather than renaming something GTK expects.

`window = self.props.active_window`
This asks GTK whether the app already has an active window.

`if window is None:`
If there is no window yet, create the launcher window.

`window = LauncherWindow(self)`
This constructs the main chooser window and associates it with the application.

`window.present()`
This is the important final step. Whether the window was newly created or already existed, `present()` brings it forward and shows it appropriately. The reasoning is: activation should always surface the app, not silently do nothing.

**`main()`**

`install_app_theme_css()`
This installs global CSS before the app starts running. That means all later-created windows can use the shared theme classes immediately. This is better than installing theme CSS per window because it avoids duplication and keeps styling centralized.

`app = PatienceApplication()`
Construct the application object.

`return app.run(None)`
This starts GTK’s main loop and hands control to the framework. From this point on, GTK dispatches events and calls hooks like `do_activate`.

**Why this file is small**

This file is deliberately thin. That is a good design choice because:
1. startup logic stays easy to reason about
2. UI construction is separated into window.py
3. styling is separated into `ui/theme.py`
4. game-specific behavior stays out of the application bootstrap

So the architectural role of app.py is “bootstrap and hand off”, not “contain logic”.

**Mental model**

A useful way to think about it is:

1. Python starts in `main()`
2. shared CSS is installed
3. the GTK app object is created
4. GTK activates the app
5. `do_activate()` ensures there is a launcher window
6. the launcher window is presented to the user

**Good notes to keep**

- app.py owns process startup, not gameplay.
- `gi.require_version` must happen before GTK imports.
- `Gtk.Application` is used for lifecycle and desktop integration.
- `do_activate()` is the framework entry hook for showing the main window.
- `present()` is used both for first show and re-activation.
- theme CSS is installed once globally at startup.

---

[Previous: index](index.md) | [Index](index.md) | [Next: window.py notes](window.py.md)
