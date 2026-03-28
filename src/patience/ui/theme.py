import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

from gi.repository import Gdk, Gtk  # noqa: E402

_APP_THEME_CSS_INSTALLED = False


def install_app_theme_css() -> None:
    global _APP_THEME_CSS_INSTALLED
    if _APP_THEME_CSS_INSTALLED:
        return

    display = Gdk.Display.get_default()
    if display is None:
        return

    css = Gtk.CssProvider()
    css.load_from_data(
        b"""
        @media (prefers-color-scheme: light) {
            .table-window {
                background-color: #dce6d7;
                background-image: linear-gradient(
                    180deg,
                    #edf3e9 0%,
                    #dfe9d9 38%,
                    #d3e0cd 100%
                );
            }

            .table-window .pile-frame {
                background: rgba(255, 255, 255, 0.58);
                border: 1px solid rgba(47, 86, 52, 0.22);
                border-radius: 10px;
                box-shadow: 0 1px 0 rgba(255, 255, 255, 0.35);
            }

            .table-window .rules-panel {
                background: rgba(248, 251, 246, 0.72);
                border: 1px solid rgba(47, 86, 52, 0.24);
            }

            .table-window .rules-panel-header,
            .table-window .rules-panel-icon {
                color: #1d5a33;
            }
        }

        @media (prefers-color-scheme: dark) {
            .table-window {
                background-color: #132219;
                background-image: linear-gradient(
                    180deg,
                    #1b2d22 0%,
                    #14251b 42%,
                    #0e1b14 100%
                );
            }

            .table-window .pile-frame {
                background: rgba(18, 31, 24, 0.68);
                border: 1px solid rgba(133, 181, 140, 0.18);
                border-radius: 10px;
                box-shadow: 0 1px 0 rgba(255, 255, 255, 0.03);
            }

            .table-window .rules-panel {
                background: rgba(18, 31, 24, 0.78);
                border: 1px solid rgba(133, 181, 140, 0.22);
            }

            .table-window .rules-panel-header,
            .table-window .rules-panel-icon {
                color: #9ed0a4;
            }
        }
        """
    )
    Gtk.StyleContext.add_provider_for_display(
        display,
        css,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
    _APP_THEME_CSS_INSTALLED = True
