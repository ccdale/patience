from collections.abc import Callable

import gi
from ccacards.card import Card
from ccacards.pile import Pile

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk  # noqa: E402

from patience.ui.cards import CARD_H, CARD_W  # noqa: E402

TABLEAU_COL_GAP = 14
FACE_DOWN_OVERLAP = 22  # px of a face-down card visible beneath the next
FACE_UP_OVERLAP = 38  # px of a face-up card visible beneath the next


def build_named_pile(
    title: str,
    pile: Pile,
    card_builder: Callable[[Card | None], Gtk.Widget],
    on_click: Callable[[], None] | None = None,
    selected: bool = False,
) -> Gtk.Widget:
    frame = Gtk.Frame()
    frame.set_size_request(CARD_W, -1)
    if selected:
        frame.add_css_class("selected-pile")

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    box.set_margin_top(8)
    box.set_margin_bottom(8)
    box.set_margin_start(8)
    box.set_margin_end(8)

    label = Gtk.Label(label=title)
    label.add_css_class("caption")
    label.set_halign(Gtk.Align.START)
    box.append(label)

    box.append(card_builder(pile.peek()))

    count = Gtk.Label(label=f"{len(pile)} cards")
    count.add_css_class("dim-label")
    count.add_css_class("caption")
    count.set_halign(Gtk.Align.START)
    box.append(count)

    frame.set_child(box)
    if on_click is not None:
        click = Gtk.GestureClick.new()
        click.connect("released", lambda *_args: on_click())
        frame.add_controller(click)
    return frame


def build_tableau_column(
    index: int,
    pile: Pile,
    card_builder: Callable[[Card | None], Gtk.Widget],
    on_click: Callable[[float], None] | None = None,
    selected_start_index: int | None = None,
) -> Gtk.Widget:
    frame = Gtk.Frame()
    if selected_start_index is not None:
        frame.add_css_class("selected-pile")

    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    outer.set_margin_top(8)
    outer.set_margin_bottom(8)
    outer.set_margin_start(8)
    outer.set_margin_end(8)

    label = Gtk.Label(label=f"T{index}")
    label.add_css_class("caption")
    label.set_halign(Gtk.Align.START)
    outer.append(label)

    cards = list(pile.cards)
    fixed = Gtk.Fixed()

    y = 0
    for i, card in enumerate(cards):
        widget = card_builder(card)
        if selected_start_index is not None and i >= selected_start_index:
            widget.add_css_class("selected-card")
        fixed.put(widget, 0, y)
        if i < len(cards) - 1:
            y += FACE_DOWN_OVERLAP if card.facedown else FACE_UP_OVERLAP

    total_height = y + CARD_H
    fixed.set_size_request(CARD_W, total_height)

    if on_click is not None:
        click = Gtk.GestureClick.new()
        click.connect("released", lambda _gesture, _n_press, _x, y_pos: on_click(y_pos))
        fixed.add_controller(click)

    outer.append(fixed)
    frame.set_child(outer)
    return frame
