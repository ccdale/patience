from dataclasses import dataclass
from pathlib import Path

import gi

from ccacards.card import Card
from ccacards.pack import Pack
from ccacards.pile import Pile

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk  # noqa: E402


@dataclass(frozen=True)
class PatienceState:
    stock: Pile
    waste: Pile
    foundations: tuple[Pile, Pile, Pile, Pile]
    tableau: tuple[Pile, Pile, Pile, Pile, Pile, Pile, Pile]


def create_initial_state() -> PatienceState:
    pack = Pack()
    pack.shuffle(times=3)

    foundations = tuple(Pile() for _ in range(4))
    tableau = tuple(Pile() for _ in range(7))
    waste = Pile()
    stock = Pile()

    for column, pile in enumerate(tableau, start=1):
        for depth in range(column):
            card = pack.deal()
            if depth < column - 1 and not card.facedown:
                card.flip()
            pile.append(card)

    while len(pack) > 0:
        card = pack.deal()
        if not card.facedown:
            card.flip()
        stock.append(card)

    return PatienceState(
        stock=stock,
        waste=waste,
        foundations=foundations,
        tableau=tableau,
    )


class PatienceWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application, parent: Gtk.Window | None = None) -> None:
        super().__init__(application=app)
        self.set_title("Patience")
        self.set_default_size(1120, 760)

        if parent is not None:
            self.set_transient_for(parent)

        self._state = create_initial_state()
        self._card_data_dir = self._resolve_card_data_dir()

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(18)
        root.set_margin_bottom(18)
        root.set_margin_start(18)
        root.set_margin_end(18)

        title = Gtk.Label(label="Patience")
        title.add_css_class("title-2")
        title.set_halign(Gtk.Align.START)
        root.append(title)

        subtitle = Gtk.Label(
            label="First layout: stock, waste, foundations and tableau built from ccacards deck and piles."
        )
        subtitle.add_css_class("dim-label")
        subtitle.set_halign(Gtk.Align.START)
        subtitle.set_wrap(True)
        root.append(subtitle)

        board = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        board.append(self._build_top_row())
        board.append(self._build_tableau_row())
        root.append(board)

        self.set_child(root)

    def _build_top_row(self) -> Gtk.Widget:
        row = Gtk.Grid(column_spacing=14)

        row.attach(self._build_named_pile("Stock", self._state.stock), 0, 0, 1, 1)
        row.attach(self._build_named_pile("Waste", self._state.waste), 1, 0, 1, 1)

        spacer = Gtk.Box(hexpand=True)
        row.attach(spacer, 2, 0, 1, 1)

        for idx, pile in enumerate(self._state.foundations, start=3):
            row.attach(self._build_named_pile(f"Foundation {idx - 2}", pile), idx, 0, 1, 1)

        return row

    def _build_tableau_row(self) -> Gtk.Widget:
        row = Gtk.Grid(column_spacing=14)
        for column, pile in enumerate(self._state.tableau):
            row.attach(self._build_tableau_column(column + 1, pile), column, 0, 1, 1)
        return row

    def _build_tableau_column(self, index: int, pile: Pile) -> Gtk.Widget:
        frame = Gtk.Frame()

        column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        column.set_margin_top(8)
        column.set_margin_bottom(8)
        column.set_margin_start(8)
        column.set_margin_end(8)

        label = Gtk.Label(label=f"T{index}")
        label.add_css_class("caption")
        label.set_halign(Gtk.Align.START)
        column.append(label)

        cards = list(pile.cards)
        start = max(0, len(cards) - 5)
        for card in cards[start:]:
            column.append(self._build_card_widget(card, stacked=True))

        frame.set_child(column)
        return frame

    def _build_named_pile(self, title: str, pile: Pile) -> Gtk.Widget:
        frame = Gtk.Frame()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        label = Gtk.Label(label=title)
        label.add_css_class("caption")
        label.set_halign(Gtk.Align.START)
        box.append(label)

        card = pile.peek()
        box.append(self._build_card_widget(card, stacked=False))

        count = Gtk.Label(label=f"{len(pile)} cards")
        count.add_css_class("dim-label")
        count.add_css_class("caption")
        count.set_halign(Gtk.Align.START)
        box.append(count)

        frame.set_child(box)
        return frame

    def _build_card_widget(self, card: Card | None, stacked: bool) -> Gtk.Widget:
        image_path = self._resolve_card_image_path(card)
        if image_path is not None:
            image = Gtk.Image.new_from_file(str(image_path))
            image.set_pixel_size(90 if stacked else 110)
            return image

        fallback = Gtk.Box()
        fallback.set_size_request(90 if stacked else 110, 150 if stacked else 170)
        fallback.add_css_class("card")
        fallback.add_css_class("frame")

        text = "Empty" if card is None else str(card)
        label = Gtk.Label(label=text)
        label.set_wrap(True)
        fallback.append(label)
        return fallback

    def _resolve_card_data_dir(self) -> Path | None:
        direct_path = Path(Card(1).imagefile).parent
        if (direct_path / "back.png").is_file():
            return direct_path

        try:
            import ccacards
        except Exception:
            return None

        package_root = Path(ccacards.__file__).resolve().parent.parent
        data_dir = package_root / "data"
        if (data_dir / "back.png").is_file():
            return data_dir
        return None

    def _resolve_card_image_path(self, card: Card | None) -> Path | None:
        if self._card_data_dir is None:
            return None

        filename = "0.png"
        if card is not None:
            filename = "back.png" if card.facedown else Path(card.imagefile).name

        image_path = self._card_data_dir / filename
        if image_path.is_file():
            return image_path
        return None


def launch(parent_window: Gtk.Window) -> None:
    app = parent_window.get_application()
    if app is None:
        raise RuntimeError("Parent window has no associated GTK application.")

    game_window = PatienceWindow(app=app, parent=parent_window)
    game_window.present()
