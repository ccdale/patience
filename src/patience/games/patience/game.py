from dataclasses import dataclass

import gi
from ccacards.card import Card
from ccacards.pack import Pack
from ccacards.pile import Pile

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gdk, Gtk  # noqa: E402

from patience.ui.cards import build_card_widget, resolve_card_data_dir  # noqa: E402
from patience.ui.help import build_rules_panel  # noqa: E402
from patience.ui.piles import (  # noqa: E402
    TABLEAU_COL_GAP,
    build_named_pile,
    build_tableau_column,
)

DRAW_COUNT = 3


@dataclass(frozen=True)
class PatienceState:
    stock: Pile
    waste: Pile
    foundations: tuple[Pile, Pile, Pile, Pile]
    tableau: tuple[Pile, Pile, Pile, Pile, Pile, Pile, Pile]


@dataclass
class Selection:
    source: str  # "waste", "foundation", "tableau"
    pile_index: int
    start_index: int | None = None


def is_red(card: Card) -> bool:
    return card.suit in {"Hearts", "Diamonds"}


def can_place_on_foundation(card: Card, foundation_top: Card | None) -> bool:
    if foundation_top is None:
        return card.value == 0  # Ace
    return card.suit == foundation_top.suit and card.value == foundation_top.value + 1


def can_place_on_tableau(card: Card, tableau_top: Card | None) -> bool:
    if tableau_top is None:
        return card.value == 12  # King
    return is_red(card) != is_red(tableau_top) and card.value == tableau_top.value - 1


def is_valid_tableau_run(cards: list[Card]) -> bool:
    if not cards:
        return False
    if any(card.facedown for card in cards):
        return False
    for idx in range(1, len(cards)):
        prev = cards[idx - 1]
        cur = cards[idx]
        if is_red(prev) == is_red(cur) or cur.value != prev.value - 1:
            return False
    return True


def draw_three_from_stock(stock: Pile, waste: Pile) -> bool:
    if len(stock) == 0:
        return False

    for _ in range(min(DRAW_COUNT, len(stock))):
        card = stock.pop()
        if card.facedown:
            card.flip()
        waste.append(card)
    return True


def redeal_waste_to_stock(stock: Pile, waste: Pile) -> bool:
    if len(stock) != 0 or len(waste) == 0:
        return False

    while len(waste) > 0:
        card = waste.pop()
        if not card.facedown:
            card.flip()
        stock.append(card)
    return True


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
        self.set_default_size(756, 900)
        self.add_css_class("table-window")

        if parent is not None:
            self.set_transient_for(parent)

        self._state = create_initial_state()
        self._card_data_dir = resolve_card_data_dir()
        self._selection: Selection | None = None
        self._install_selection_css()

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.set_margin_top(18)
        root.set_margin_bottom(18)
        root.set_margin_start(18)
        root.set_margin_end(18)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        title = Gtk.Label(label="Patience")
        title.add_css_class("title-2")
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        header.append(title)

        new_game_button = Gtk.Button(label="New Game")
        new_game_button.connect("clicked", self._on_new_game_clicked)
        header.append(new_game_button)

        root.append(header)

        self._status = Gtk.Label(label="Draw-3, unlimited redeals, auto-foundation")
        self._status.add_css_class("dim-label")
        self._status.set_halign(Gtk.Align.START)
        root.append(self._status)

        root.append(
            build_rules_panel(
                "Foundations: build up by suit from Ace to King.\n"
                "Tableau: build down by alternating color; only Kings fill empty columns.\n"
                "You may move a single face-up card or a valid face-up run between tableau columns.\n"
                "Stock: draw 3 cards to the waste with unlimited redeals.\n"
                "Foundation moves are applied automatically when available."
            )
        )

        self._board = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._board.set_halign(Gtk.Align.START)
        root.append(self._board)

        self._refresh_board()

        self.set_child(root)

    def _refresh_board(self) -> None:
        child = self._board.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._board.remove(child)
            child = nxt
        self._board.append(self._build_board_grid())

    def _build_board_grid(self) -> Gtk.Widget:
        # Shared 7-column grid:
        # top:    Stock(0), Waste(1), gap(2), F1(3), F2(4), F3(5), F4(6)
        # bottom: T1(0),    T2(1),    T3(2),  T4(3), T5(4), T6(5), T7(6)
        grid = Gtk.Grid(column_spacing=TABLEAU_COL_GAP, row_spacing=14)
        grid.set_column_homogeneous(False)

        grid.attach(
            build_named_pile(
                "Stock",
                self._state.stock,
                self._card_widget,
                on_click=self._on_stock_clicked,
                selected=False,
            ),
            0,
            0,
            1,
            1,
        )
        grid.attach(
            build_named_pile(
                "Waste",
                self._state.waste,
                self._card_widget,
                on_click=self._on_waste_clicked,
                selected=self._is_selected_named("waste", 0),
            ),
            1,
            0,
            1,
            1,
        )

        for idx, pile in enumerate(self._state.foundations):
            grid.attach(
                build_named_pile(
                    f"Foundation {idx + 1}",
                    pile,
                    self._card_widget,
                    on_click=lambda foundation_idx=idx: self._on_foundation_clicked(
                        foundation_idx
                    ),
                    selected=self._is_selected_named("foundation", idx),
                ),
                idx + 3,
                0,
                1,
                1,
            )

        for column, pile in enumerate(self._state.tableau):
            grid.attach(
                build_tableau_column(
                    column + 1,
                    pile,
                    self._card_widget,
                    on_click=lambda y_pos, tableau_idx=column: self._on_tableau_clicked(
                        tableau_idx, y_pos
                    ),
                    selected_start_index=self._selected_tableau_start(column),
                ),
                column,
                1,
                1,
                1,
            )

        return grid

    def _card_widget(self, card: Card | None) -> Gtk.Widget:
        return build_card_widget(card, self._card_data_dir)

    def _on_new_game_clicked(self, _button: Gtk.Button) -> None:
        self._state = create_initial_state()
        self._selection = None
        self._set_status("Draw-3, unlimited redeals, auto-foundation")
        self._refresh_board()

    def _install_selection_css(self) -> None:
        css = Gtk.CssProvider()
        css.load_from_data(
            b"""
            .selected-pile {
                box-shadow: 0 0 0 2px #2a7fff;
                border-radius: 8px;
                background: alpha(#2a7fff, 0.08);
            }
            .selected-card {
                box-shadow: inset 0 0 0 2px #2a7fff;
                border-radius: 6px;
            }
            """
        )
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display,
                css,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    def _is_selected_named(self, source: str, pile_index: int) -> bool:
        selection = self._selection
        return bool(
            selection
            and selection.source == source
            and selection.pile_index == pile_index
        )

    def _selected_tableau_start(self, pile_index: int) -> int | None:
        selection = self._selection
        if selection is None:
            return None
        if selection.source != "tableau" or selection.pile_index != pile_index:
            return None
        return selection.start_index

    def _on_stock_clicked(self) -> None:
        changed = draw_three_from_stock(self._state.stock, self._state.waste)
        if not changed:
            changed = redeal_waste_to_stock(self._state.stock, self._state.waste)
        if changed:
            self._selection = None
            self._auto_move_to_foundations()
            self._refresh_board()

    def _on_waste_clicked(self) -> None:
        if len(self._state.waste) == 0:
            self._selection = None
            return
        if self._selection and self._selection.source == "waste":
            self._selection = None
            self._set_status("Selection cleared")
            return

        self._selection = Selection(source="waste", pile_index=0)
        self._set_status("Selected waste top")

    def _on_foundation_clicked(self, foundation_idx: int) -> None:
        if self._selection is not None:
            moved = self._move_selection_to_foundation(foundation_idx)
            if moved:
                self._selection = None
                self._auto_move_to_foundations()
                self._refresh_board()
            return

        source = self._state.foundations[foundation_idx]
        if len(source) == 0:
            return

        self._selection = Selection(source="foundation", pile_index=foundation_idx)
        self._set_status(f"Selected foundation {foundation_idx + 1} top")

    def _on_tableau_clicked(self, tableau_idx: int, y_pos: float) -> None:
        pile = self._state.tableau[tableau_idx]
        clicked_index = self._tableau_card_index_from_y(pile, y_pos)

        if self._selection is not None:
            moved = self._move_selection_to_tableau(tableau_idx)
            if moved:
                self._selection = None
                self._auto_move_to_foundations()
                self._refresh_board()
            return

        if clicked_index is None:
            return

        cards = pile.cards
        clicked_card = cards[clicked_index]

        if clicked_card.facedown:
            if clicked_index == len(cards) - 1:
                clicked_card.flip()
                self._auto_move_to_foundations()
                self._refresh_board()
            return

        self._selection = Selection(
            source="tableau",
            pile_index=tableau_idx,
            start_index=clicked_index,
        )
        if clicked_index == len(cards) - 1:
            self._set_status(f"Selected T{tableau_idx + 1} top card")
        else:
            self._set_status(f"Selected run from T{tableau_idx + 1}")

    def _move_selection_to_foundation(self, foundation_idx: int) -> bool:
        selection = self._selection
        if selection is None:
            return False

        dest = self._state.foundations[foundation_idx]
        card = self._peek_selected_card(selection)
        if card is None:
            return False

        if not can_place_on_foundation(card, dest.peek()):
            self._set_status("Illegal move to foundation")
            return False

        if not self._selection_is_single_card(selection):
            self._set_status("Only single cards can move to foundation")
            return False

        moved = self._pop_selected_cards(selection)
        if len(moved) != 1:
            return False
        dest.append(moved[0])
        self._post_source_cleanup(selection)
        return True

    def _move_selection_to_tableau(self, tableau_idx: int) -> bool:
        selection = self._selection
        if selection is None:
            return False

        if selection.source == "tableau" and selection.pile_index == tableau_idx:
            self._set_status("Cannot move onto same tableau")
            return False

        cards = self._get_selected_cards(selection)
        if not cards or not is_valid_tableau_run(cards):
            self._set_status("Selected run is not valid")
            return False

        dest = self._state.tableau[tableau_idx]
        if not can_place_on_tableau(cards[0], dest.peek()):
            self._set_status("Illegal move to tableau")
            return False

        moved = self._pop_selected_cards(selection)
        for card in moved:
            dest.append(card)
        self._post_source_cleanup(selection)
        return True

    def _auto_move_to_foundations(self) -> None:
        moved = True
        while moved:
            moved = False

            waste_top = self._state.waste.peek()
            if waste_top is not None:
                foundation_idx = self._find_foundation_for_card(waste_top)
                if foundation_idx is not None:
                    card = self._state.waste.pop()
                    self._state.foundations[foundation_idx].append(card)
                    moved = True
                    continue

            for pile in self._state.tableau:
                top = pile.peek()
                if top is None or top.facedown:
                    continue
                foundation_idx = self._find_foundation_for_card(top)
                if foundation_idx is None:
                    continue
                card = pile.pop()
                self._state.foundations[foundation_idx].append(card)
                if len(pile) > 0 and pile.peek().facedown:
                    pile.peek().flip()
                moved = True
                break

    def _find_foundation_for_card(self, card: Card) -> int | None:
        for idx, foundation in enumerate(self._state.foundations):
            if can_place_on_foundation(card, foundation.peek()):
                return idx
        return None

    def _peek_selected_card(self, selection: Selection) -> Card | None:
        cards = self._get_selected_cards(selection)
        return cards[0] if cards else None

    def _selection_is_single_card(self, selection: Selection) -> bool:
        cards = self._get_selected_cards(selection)
        return len(cards) == 1

    def _get_selected_cards(self, selection: Selection) -> list[Card]:
        if selection.source == "waste":
            top = self._state.waste.peek()
            return [top] if top is not None else []

        if selection.source == "foundation":
            top = self._state.foundations[selection.pile_index].peek()
            return [top] if top is not None else []

        if selection.source == "tableau":
            pile_cards = self._state.tableau[selection.pile_index].cards
            if selection.start_index is None:
                return []
            return list(pile_cards[selection.start_index :])

        return []

    def _pop_selected_cards(self, selection: Selection) -> list[Card]:
        if selection.source == "waste":
            return [self._state.waste.pop()]

        if selection.source == "foundation":
            return [self._state.foundations[selection.pile_index].pop()]

        source = self._state.tableau[selection.pile_index]
        if selection.start_index is None:
            return []

        count = len(source.cards) - selection.start_index
        moved: list[Card] = []
        for _ in range(count):
            moved.append(source.pop())
        moved.reverse()
        return moved

    def _post_source_cleanup(self, selection: Selection) -> None:
        if selection.source != "tableau":
            return
        source = self._state.tableau[selection.pile_index]
        top = source.peek()
        if top is not None and top.facedown:
            top.flip()

    def _tableau_card_index_from_y(self, pile: Pile, y_pos: float) -> int | None:
        cards = pile.cards
        if not cards:
            return None

        y = 0
        starts: list[int] = []
        for idx, card in enumerate(cards):
            starts.append(y)
            if idx < len(cards) - 1:
                y += 22 if card.facedown else 38

        clicked = int(y_pos)
        for idx in range(len(starts) - 1, -1, -1):
            if clicked >= starts[idx]:
                return idx
        return None

    def _set_status(self, message: str) -> None:
        self._status.set_text(message)


def launch(parent_window: Gtk.Window) -> None:
    app = parent_window.get_application()
    if app is None:
        raise RuntimeError("Parent window has no associated GTK application.")

    game_window = PatienceWindow(app=app, parent=parent_window)
    game_window.present()
