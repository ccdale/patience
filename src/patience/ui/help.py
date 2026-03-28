import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk  # noqa: E402


def build_rules_panel(text: str, title: str = "Rules") -> Gtk.Widget:
    expander = Gtk.Expander(label=title)
    expander.set_expanded(False)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    box.set_margin_top(8)
    box.set_margin_bottom(8)
    box.set_margin_start(12)
    box.set_margin_end(12)

    help_text = Gtk.Label(label=text)
    help_text.set_wrap(True)
    help_text.set_halign(Gtk.Align.START)
    help_text.set_xalign(0)

    box.append(help_text)
    expander.set_child(box)
    return expander
