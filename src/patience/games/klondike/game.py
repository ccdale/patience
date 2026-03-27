import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk  # noqa: E402


class KlondikeWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application, parent: Gtk.Window | None = None) -> None:
        super().__init__(application=app)
        self.set_title("Klondike")
        self.set_default_size(900, 650)

        if parent is not None:
            self.set_transient_for(parent)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(20)
        root.set_margin_bottom(20)
        root.set_margin_start(20)
        root.set_margin_end(20)

        title = Gtk.Label(label="Klondike")
        title.add_css_class("title-2")
        title.set_halign(Gtk.Align.START)

        subtitle = Gtk.Label(
            label="Initial game shell. Tableau, stock, waste, and foundation logic will be added next."
        )
        subtitle.add_css_class("dim-label")
        subtitle.set_halign(Gtk.Align.START)
        subtitle.set_wrap(True)

        root.append(title)
        root.append(subtitle)
        self.set_child(root)


def launch(parent_window: Gtk.Window) -> None:
    app = parent_window.get_application()
    if app is None:
        raise RuntimeError("Parent window has no associated GTK application.")

    game_window = KlondikeWindow(app=app, parent=parent_window)
    game_window.present()
