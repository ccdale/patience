from dataclasses import dataclass

import gi
from ccacards.card import Card
from ccacards.pack import Pack
from ccacards.pile import Pile

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

from gi.repository import Gdk, Gtk  # noqa: E402

from patience.ui.cards import build_card_widget, resolve_card_data_dir
from patience.ui.help import build_rules_panel
from patience.ui.piles import (
    FACE_UP_OVERLAP,
    TABLEAU_COL_GAP,
    build_named_pile,
    build_tableau_column,
)

FREE_CELLS = 4
FOUNDATIONS = 4
TABLEAU_COLS = 8


@dataclass(frozen=True)
class FreeCellState:
    free_cells: tuple[Pile, Pile, Pile, Pile]
    foundations: tuple[Pile, Pile, Pile, Pile]
    tableau: tuple[Pile, ...]


@dataclass
class Selection:
    source: str  # "freecell", "foundation", "tableau"
    pile_index: int
    start_index: int | None = None


def is_red(card: Card) -> bool:
    return card.suit in {"Hearts", "Diamonds"}


def can_place_on_foundation(card: Card, foundation_top: Card | None) -> bool:
    if foundation_top is None:
        return card.value == 0
    return card.suit == foundation_top.suit and card.value == foundation_top.value + 1


def can_place_on_tableau(card: Card, tableau_top: Card | None) -> bool:
    if tableau_top is None:
        return True
    return is_red(card) != is_red(tableau_top) and card.value == tableau_top.value - 1


def is_valid_tableau_run(cards: list[Card]) -> bool:
    if not cards:
        return False
    if any(card.facedown for card in cards):
        return False
    for idx in range(1, len(cards)):
        prev = cards[idx - 1]
        cur = cards[idx]
        if not can_place_on_tableau(cur, prev):
            return False
    return True


def max_movable_cards(
    empty_free_cells: int, empty_tableau: int, destination_is_empty: bool
) -> int:
    usable_empty_tableau = empty_tableau - 1 if destination_is_empty else empty_tableau
    if usable_empty_tableau < 0:
        usable_empty_tableau = 0
    return (empty_free_cells + 1) * (2**usable_empty_tableau)


def create_initial_state() -> FreeCellState:
    pack = Pack()
    pack.shuffle(times=3)

    free_cells = tuple(Pile() for _ in range(FREE_CELLS))
    foundations = tuple(Pile() for _ in range(FOUNDATIONS))
    tableau = tuple(Pile() for _ in range(TABLEAU_COLS))

    cards: list[Card] = []
    while len(pack) > 0:
        card = pack.deal()
        if card.facedown:
            card.flip()
        cards.append(card)

    for idx, card in enumerate(cards):
        tableau[idx % TABLEAU_COLS].append(card)

    return FreeCellState(
        free_cells=free_cells,
        foundations=foundations,
        tableau=tableau,
    )


class FreeCellWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application, parent: Gtk.Window | None = None) -> None:
        super().__init__(application=app)
        self.set_title("FreeCell")
        self.set_default_size(1280, 920)
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

        title = Gtk.Label(label="FreeCell")
        title.add_css_class("title-2")
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        header.append(title)

        new_game_button = Gtk.Button(label="New Game")
        new_game_button.connect("clicked", self._on_new_game_clicked)
        header.append(new_game_button)

        root.append(header)

        self._status = Gtk.Label(
            label="4 free cells, 8 cascades, alternating-color tableau, manual foundations"
        )
        self._status.add_css_class("dim-label")
        self._status.set_halign(Gtk.Align.START)
        root.append(self._status)

        root.append(
            build_rules_panel(
                "Foundations: build up by suit from Ace to King.\n"
                "Tableau: build down by alternating color. Any card may fill an empty cascade.\n"
                "Free cells: each cell holds one card.\n"
                "You may move valid tableau runs when enough empty free cells and cascades are available.\n"
                "Foundations are manual, not automatic."
            )
        )

        self._board = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._board.set_halign(Gtk.Align.START)
        root.append(self._board)

        self._refresh_board()
        self.set_child(root)
        self.maximize()

    def _refresh_board(self) -> None:
        child = self._board.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._board.remove(child)
            child = nxt
        self._board.append(self._build_board())

    def _build_board(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)

        top_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=TABLEAU_COL_GAP,
        )
        for idx, pile in enumerate(self._state.free_cells):
            top_row.append(
                build_named_pile(
                    f"Cell {idx + 1}",
                    pile,
                    self._card_widget,
                    on_click=lambda freecell_idx=idx: self._on_free_cell_clicked(
                        freecell_idx
                    ),
                    selected=self._is_selected_named("freecell", idx),
                )
            )

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        top_row.append(spacer)

        for idx, pile in enumerate(self._state.foundations):
            top_row.append(
                build_named_pile(
                    f"Foundation {idx + 1}",
                    pile,
                    self._card_widget,
                    on_click=lambda foundation_idx=idx: self._on_foundation_clicked(
                        foundation_idx
                    ),
                    selected=self._is_selected_named("foundation", idx),
                )
            )

        outer.append(top_row)

        tableau_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=TABLEAU_COL_GAP,
        )
        for column, pile in enumerate(self._state.tableau):
            tableau_row.append(
                build_tableau_column(
                    column + 1,
                    pile,
                    self._card_widget,
                    on_click=lambda y_pos, tableau_idx=column: self._on_tableau_clicked(
                        tableau_idx, y_pos
                    ),
                    selected_start_index=self._selected_tableau_start(column),
                )
            )

        outer.append(tableau_row)
        return outer

    def _card_widget(self, card: Card | None) -> Gtk.Widget:
        return build_card_widget(card, self._card_data_dir)

    def _on_new_game_clicked(self, _button: Gtk.Button) -> None:
        self._state = create_initial_state()
        self._selection = None
        self._set_status(
            "4 free cells, 8 cascades, alternating-color tableau, manual foundations"
        )
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

    def _on_free_cell_clicked(self, freecell_idx: int) -> None:
        if self._selection is not None:
            moved = self._move_selection_to_free_cell(freecell_idx)
            if moved:
                self._selection = None
                self._check_win()
                self._refresh_board()
            return

        source = self._state.free_cells[freecell_idx]
        if len(source) == 0:
            return

        if self._selection and self._selection.source == "freecell":
            self._selection = None
            self._set_status("Selection cleared")
            return

        self._selection = Selection(source="freecell", pile_index=freecell_idx)
        self._set_status(f"Selected free cell {freecell_idx + 1}")
        self._refresh_board()

    def _on_foundation_clicked(self, foundation_idx: int) -> None:
        if self._selection is not None:
            moved = self._move_selection_to_foundation(foundation_idx)
            if moved:
                self._selection = None
                self._check_win()
                self._refresh_board()
            return

        source = self._state.foundations[foundation_idx]
        if len(source) == 0:
            return

        self._selection = Selection(source="foundation", pile_index=foundation_idx)
        self._set_status(f"Selected foundation {foundation_idx + 1} top")
        self._refresh_board()

    def _on_tableau_clicked(self, tableau_idx: int, y_pos: float) -> None:
        pile = self._state.tableau[tableau_idx]

        if self._selection is not None:
            moved = self._move_selection_to_tableau(tableau_idx)
            if moved:
                self._selection = None
                self._check_win()
                self._refresh_board()
            return

        clicked_index = self._tableau_card_index_from_y(pile, y_pos)
        if clicked_index is None:
            return

        self._selection = Selection(
            source="tableau",
            pile_index=tableau_idx,
            start_index=clicked_index,
        )
        selected_count = len(pile.cards) - clicked_index
        movable_capacity = self._selected_move_capacity(tableau_idx)
        if clicked_index == len(pile.cards) - 1:
            self._set_status(
                f"Selected T{tableau_idx + 1} top card; current run capacity is {movable_capacity}"
            )
        else:
            self._set_status(
                f"Selected run of {selected_count} from T{tableau_idx + 1}; current run capacity is {movable_capacity}"
            )
        self._refresh_board()

    def _move_selection_to_free_cell(self, freecell_idx: int) -> bool:
        selection = self._selection
        if selection is None:
            return False
        if selection.source == "freecell" and selection.pile_index == freecell_idx:
            self._selection = None
            self._set_status("Selection cleared")
            self._refresh_board()
            return False

        dest = self._state.free_cells[freecell_idx]
        if len(dest) != 0:
            self._set_status("Free cell is occupied")
            return False
        if not self._selection_is_single_card(selection):
            self._set_status("Only single cards can move to a free cell")
            return False

        moved = self._pop_selected_cards(selection)
        if len(moved) != 1:
            return False
        dest.append(moved[0])
        return True

    def _move_selection_to_foundation(self, foundation_idx: int) -> bool:
        selection = self._selection
        if selection is None:
            return False

        if not self._selection_is_single_card(selection):
            self._set_status("Only single cards can move to foundation")
            return False

        card = self._peek_selected_card(selection)
        if card is None:
            return False

        dest = self._state.foundations[foundation_idx]
        if not can_place_on_foundation(card, dest.peek()):
            self._set_status("Illegal move to foundation")
            return False

        moved = self._pop_selected_cards(selection)
        if len(moved) != 1:
            return False
        dest.append(moved[0])
        return True

    def _move_selection_to_tableau(self, tableau_idx: int) -> bool:
        selection = self._selection
        if selection is None:
            return False
        if selection.source == "tableau" and selection.pile_index == tableau_idx:
            self._set_status("Cannot move onto same tableau")
            return False

        cards = self._get_selected_cards(selection)
        if not cards:
            return False
        if len(cards) > 1 and not is_valid_tableau_run(cards):
            self._set_status("Selected run is not valid")
            return False

        dest = self._state.tableau[tableau_idx]
        if not can_place_on_tableau(cards[0], dest.peek()):
            self._set_status("Illegal move to tableau")
            return False

        if selection.source == "tableau":
            max_cards = max_movable_cards(
                empty_free_cells=self._count_empty_free_cells(),
                empty_tableau=self._count_empty_tableau(excluding=selection.pile_index),
                destination_is_empty=len(dest) == 0,
            )
            if len(cards) > max_cards:
                self._set_status(
                    f"Not enough free cells or empty cascades for that run; current limit is {max_cards}"
                )
                return False
        elif len(cards) > 1:
            self._set_status("Only tableau runs can move multiple cards")
            return False

        moved = self._pop_selected_cards(selection)
        for card in moved:
            dest.append(card)
        return True

    def _count_empty_free_cells(self) -> int:
        return sum(1 for pile in self._state.free_cells if len(pile) == 0)

    def _count_empty_tableau(self, excluding: int | None = None) -> int:
        count = 0
        for idx, pile in enumerate(self._state.tableau):
            if excluding is not None and idx == excluding:
                continue
            if len(pile) == 0:
                count += 1
        return count

    def _selected_move_capacity(self, source_tableau_idx: int) -> int:
        return max_movable_cards(
            empty_free_cells=self._count_empty_free_cells(),
            empty_tableau=self._count_empty_tableau(excluding=source_tableau_idx),
            destination_is_empty=False,
        )

    def _peek_selected_card(self, selection: Selection) -> Card | None:
        cards = self._get_selected_cards(selection)
        return cards[0] if cards else None

    def _selection_is_single_card(self, selection: Selection) -> bool:
        return len(self._get_selected_cards(selection)) == 1

    def _get_selected_cards(self, selection: Selection) -> list[Card]:
        if selection.source == "freecell":
            top = self._state.free_cells[selection.pile_index].peek()
            return [top] if top is not None else []

        if selection.source == "foundation":
            top = self._state.foundations[selection.pile_index].peek()
            return [top] if top is not None else []

        if selection.source == "tableau":
            if selection.start_index is None:
                return []
            return list(
                self._state.tableau[selection.pile_index].cards[selection.start_index :]
            )

        return []

    def _pop_selected_cards(self, selection: Selection) -> list[Card]:
        if selection.source == "freecell":
            return [self._state.free_cells[selection.pile_index].pop()]

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

    def _tableau_card_index_from_y(self, pile: Pile, y_pos: float) -> int | None:
        cards = pile.cards
        if not cards:
            return None

        starts: list[int] = []
        y = 0
        for idx in range(len(cards)):
            starts.append(y)
            if idx < len(cards) - 1:
                y += FACE_UP_OVERLAP

        clicked = int(y_pos)
        for idx in range(len(starts) - 1, -1, -1):
            if clicked >= starts[idx]:
                return idx
        return None

    def _check_win(self) -> None:
        total = sum(len(foundation) for foundation in self._state.foundations)
        if total == 52:
            self._set_status("You win!")

    def _set_status(self, message: str) -> None:
        self._status.set_text(message)


def launch(parent_window: Gtk.Window) -> None:
    app = parent_window.get_application()
    if app is None:
        raise RuntimeError("Parent window has no associated GTK application.")

    game_window = FreeCellWindow(app=app, parent=parent_window)
    game_window.present()
