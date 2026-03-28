import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from patience.ui.theme import install_app_theme_css
from patience.window import LauncherWindow


class PatienceApplication(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id="org.cca.patience")

    def do_activate(self) -> None:  # noqa: N802 (Gtk virtual method name)
        window = self.props.active_window
        if window is None:
            window = LauncherWindow(self)
        window.present()


def main() -> int:
    install_app_theme_css()
    app = PatienceApplication()
    return app.run(None)
