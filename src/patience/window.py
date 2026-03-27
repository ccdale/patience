import gi

from patience.games.registry import GAME_REGISTRY, GameSpec

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk  # noqa: E402


class LauncherWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application) -> None:
        super().__init__(application=app)
        self.set_title("Patience")
        self.set_default_size(840, 560)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(18)
        root.set_margin_bottom(18)
        root.set_margin_start(18)
        root.set_margin_end(18)

        title = Gtk.Label(label="Choose A Solitaire Game")
        title.set_halign(Gtk.Align.START)
        title.add_css_class("title-2")
        root.append(title)

        subtitle = Gtk.Label(
            label="Each game can be implemented as a standalone module and launched from here."
        )
        subtitle.set_halign(Gtk.Align.START)
        subtitle.add_css_class("dim-label")
        root.append(subtitle)

        listbox = Gtk.ListBox()
        listbox.add_css_class("boxed-list")
        for game in GAME_REGISTRY:
            listbox.append(self._build_game_row(game))

        root.append(listbox)
        self.set_child(root)

    def _build_game_row(self, game: GameSpec) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(10)
        box.set_margin_end(10)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title = Gtk.Label(label=game.title)
        title.set_halign(Gtk.Align.START)
        title.add_css_class("heading")
        labels.append(title)

        detail = Gtk.Label(label=game.module)
        detail.set_halign(Gtk.Align.START)
        detail.add_css_class("caption")
        detail.add_css_class("dim-label")
        labels.append(detail)

        launch = Gtk.Button(label="Launch")
        launch.set_sensitive(game.available)
        launch.connect("clicked", self._on_launch_clicked, game)

        box.append(labels)
        box.append(Gtk.Box(hexpand=True))
        box.append(launch)
        row.set_child(box)
        return row

    def _on_launch_clicked(self, _button: Gtk.Button, game: GameSpec) -> None:
        # Placeholder until game modules expose an actual launcher API.
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            buttons=Gtk.ButtonsType.OK,
            text=f"{game.title} is not wired yet.",
        )
        dialog.connect("response", lambda d, _r: d.close())
        dialog.present()
