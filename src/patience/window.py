import importlib
from importlib import resources

import gi

from patience.games.registry import GAME_ICON_FILENAME, GAME_REGISTRY, GameSpec

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

        grid = Gtk.Grid(column_spacing=12, row_spacing=12)
        grid.set_hexpand(True)
        grid.set_vexpand(True)

        max_columns = 3
        for index, game in enumerate(GAME_REGISTRY):
            row = index // max_columns
            column = index % max_columns
            grid.attach(self._build_game_tile(game), column, row, 1, 1)

        root.append(grid)
        self.set_child(root)

    def _build_game_tile(self, game: GameSpec) -> Gtk.Widget:
        frame = Gtk.Frame()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_size_request(220, 140)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        icon = self._build_game_icon(game)
        header.append(icon)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        labels.set_hexpand(True)
        title = Gtk.Label(label=game.title)
        title.set_halign(Gtk.Align.START)
        title.add_css_class("heading")
        labels.append(title)

        detail = Gtk.Label(label=game.module)
        detail.set_halign(Gtk.Align.START)
        detail.add_css_class("caption")
        detail.add_css_class("dim-label")
        labels.append(detail)

        header.append(labels)

        launch = Gtk.Button(label="Launch")
        launch.set_halign(Gtk.Align.END)
        launch.set_sensitive(game.available)
        launch.connect("clicked", self._on_launch_clicked, game)

        box.append(header)
        box.append(Gtk.Box(vexpand=True))
        box.append(launch)
        frame.set_child(box)
        return frame

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

    def _find_game_icon_path(self, game: GameSpec) -> str | None:
        try:
            icon_resource = resources.files(game.module).joinpath(GAME_ICON_FILENAME)
        except (ModuleNotFoundError, TypeError):
            return None
        if not icon_resource.is_file():
            return None
        return str(icon_resource)

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

    def _show_info_dialog(self, text: str) -> None:
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            buttons=Gtk.ButtonsType.OK,
            text=text,
        )
        dialog.connect("response", lambda d, _r: d.close())
        dialog.present()
