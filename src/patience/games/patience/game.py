from dataclasses import dataclass

import gi
from ccacards.pack import Pack
from ccacards.pile import Pile

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk  # noqa: E402

from patience.ui.cards import build_card_widget, resolve_card_data_dir  # noqa: E402
from patience.ui.piles import build_named_pile, build_tableau_column  # noqa: E402

COLUMN_GAP = 14


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
        self._card_data_dir = resolve_card_data_dir()

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(18)
        root.set_margin_bottom(18)
        root.set_margin_start(18)
        root.set_margin_end(18)

        title = Gtk.Label(label="Patience")
        title.add_css_class("title-2")
        title.set_halign(Gtk.Align.START)
        root.append(title)

        root.append(self._build_board_grid())
        self.set_child(root)

    def _build_board_grid(self) -> Gtk.Widget:
        # Shared 7-column grid for alignment:
        # top:    Stock(0), Waste(1), gap(2), F1(3), F2(4), F3(5), F4(6)
        # bottom: T1(0),    T2(1),    T3(2),  T4(3), T5(4), T6(5), T7(6)
        grid = Gtk.Grid(column_spacing=COLUMN_GAP, row_spacing=14)
        grid.set_column_homogeneous(True)

        grid.attach(build_named_pile("Stock", self._state.stock, self._card_widget), 0, 0, 1, 1)
        grid.attach(build_named_pile("Waste", self._state.waste, self._card_widget), 1, 0, 1, 1)

        for idx, pile in enumerate(self._state.foundations):
            grid.attach(
                build_named_pile(f"Foundation {idx + 1}", pile, self._card_widget),
                idx + 3,
                0,
                1,
                1,
            )

        for column, pile in enumerate(self._state.tableau):
            grid.attach(
                build_tableau_column(column + 1, pile, self._card_widget),
                column,
                1,
                1,
                1,
            )

        return grid

    def _card_widget(self, card) -> Gtk.Widget:
        return build_card_widget(card, self._card_data_dir)


def launch(parent_window: Gtk.Window) -> None:
    app = parent_window.get_application()
    if app is None:
        raise RuntimeError("Parent window has no associated GTK application.")

    game_window = PatienceWindow(app=app, parent=parent_window)
    game_window.present()
