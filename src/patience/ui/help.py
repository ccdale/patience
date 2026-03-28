import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

from gi.repository import Gdk, Gtk  # noqa: E402

_RULES_PANEL_CSS_INSTALLED = False


def _ensure_rules_panel_css() -> None:
    global _RULES_PANEL_CSS_INSTALLED
    if _RULES_PANEL_CSS_INSTALLED:
        return

    display = Gdk.Display.get_default()
    if display is None:
        return

    css = Gtk.CssProvider()
    css.load_from_data(
        b"""
        .rules-panel {
            border-radius: 10px;
            border: 1px solid alpha(#0f6d3a, 0.20);
            background: alpha(#0f6d3a, 0.05);
        }
        .rules-panel-header {
            color: #0f6d3a;
            font-weight: 700;
        }
        .rules-panel-body {
            color: alpha(currentColor, 0.92);
        }
        """
    )
    Gtk.StyleContext.add_provider_for_display(
        display,
        css,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
    _RULES_PANEL_CSS_INSTALLED = True


def build_rules_panel(text: str, title: str = "Rules") -> Gtk.Widget:
    _ensure_rules_panel_css()

    frame = Gtk.Frame()
    frame.add_css_class("rules-panel")

    expander = Gtk.Expander()
    expander.set_expanded(False)

    header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    header.set_margin_top(8)
    header.set_margin_bottom(8)
    header.set_margin_start(10)
    header.set_margin_end(10)

    icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic")
    icon.set_pixel_size(16)
    icon.add_css_class("rules-panel-icon")
    header.append(icon)

    heading = Gtk.Label(label=title)
    heading.add_css_class("rules-panel-header")
    heading.set_halign(Gtk.Align.START)
    heading.set_xalign(0)
    header.append(heading)

    expander.set_label_widget(header)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    box.set_margin_top(8)
    box.set_margin_bottom(12)
    box.set_margin_start(12)
    box.set_margin_end(12)

    help_text = Gtk.Label(label=text)
    help_text.add_css_class("rules-panel-body")
    help_text.set_wrap(True)
    help_text.set_halign(Gtk.Align.START)
    help_text.set_xalign(0)
    help_text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)

    box.append(help_text)
    expander.set_child(box)
    frame.set_child(expander)
    return frame
