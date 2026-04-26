from dataclasses import dataclass

import gi
from ccacards.card import Card
from ccacards.pack import Pack
from ccacards.pile import Pile

from patience.games.undo import clone_game_state
from patience.stats import record_started, record_won
from patience.ui.cards import build_card_widget, resolve_card_data_dir
from patience.ui.help import build_rules_panel
from patience.ui.piles import TABLEAU_COL_GAP, build_named_pile, build_tableau_column

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

GAME_ID = "demon"

DRAW_COUNT = 3
RESERVE_SIZE = 13
TABLEAU_COLS = 4
RANK_NAMES = (
    "Ace",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "Jack",
    "Queen",
    "King",
)


@dataclass(frozen=True)
class DemonState:
    stock: Pile
    waste: Pile
    reserve: Pile
    foundations: tuple[Pile, Pile, Pile, Pile]
    tableau: tuple[Pile, Pile, Pile, Pile]
    foundation_base_rank: int


@dataclass
class Selection:
    source: str  # "reserve", "waste", "foundation", "tableau"
    pile_index: int
    start_index: int | None = None


def is_red(card: Card) -> bool:
    return card.suit in {"Hearts", "Diamonds"}


def can_place_on_foundation(
    card: Card, foundation_top: Card | None, foundation_base_rank: int
) -> bool:
    if foundation_top is None:
        return card.value == foundation_base_rank
    return (
        card.suit == foundation_top.suit
        and card.value == (foundation_top.value + 1) % 13
    )


def can_place_on_tableau(card: Card, tableau_top: Card | None) -> bool:
    if tableau_top is None:
        return False
    return (
        is_red(card) != is_red(tableau_top)
        and card.value == (tableau_top.value - 1) % 13
    )


def is_valid_tableau_run(cards: list[Card]) -> bool:
    if not cards:
        return False
    if any(card.facedown for card in cards):
        return False
    for idx in range(1, len(cards)):
        if not can_place_on_tableau(cards[idx], cards[idx - 1]):
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


def create_initial_state() -> DemonState:
    pack = Pack()
    pack.shuffle(times=3)

    stock = Pile()
    waste = Pile()
    reserve = Pile()
    foundations = tuple(Pile() for _ in range(4))
    tableau = tuple(Pile() for _ in range(TABLEAU_COLS))

    for reserve_index in range(RESERVE_SIZE):
        card = pack.deal()
        if reserve_index < RESERVE_SIZE - 1 and not card.facedown:
            card.flip()
        if reserve_index == RESERVE_SIZE - 1 and card.facedown:
            card.flip()
        reserve.append(card)

    base_card = pack.deal()
    if base_card.facedown:
        base_card.flip()
    foundations[0].append(base_card)

    for pile in tableau:
        card = pack.deal()
        if card.facedown:
            card.flip()
        pile.append(card)

    while len(pack) > 0:
        card = pack.deal()
        if not card.facedown:
            card.flip()
        stock.append(card)

    return DemonState(
        stock=stock,
        waste=waste,
        reserve=reserve,
        foundations=foundations,
        tableau=tableau,
        foundation_base_rank=base_card.value,
    )


def _collect_auto_moves(
    foundations: tuple[Pile, Pile, Pile, Pile],
    tableau: tuple[Pile, Pile, Pile, Pile],
    reserve: Pile,
    waste: Pile,
    foundation_base_rank: int,
) -> list[tuple[str, int, int]]:
    """Simulate the auto-move cascade and return an ordered list of
    (source, source_idx, foundation_idx) tuples without modifying state.
    Checks reserve first, then waste, then tableau."""
    found_tops: list[Card | None] = [f.peek() for f in foundations]
    moves: list[tuple[str, int, int]] = []
    moved = True

    while moved:
        moved = False

        # Check reserve first
        card = reserve.peek()
        if card is not None:
            for found_idx, found_top in enumerate(found_tops):
                if can_place_on_foundation(card, found_top, foundation_base_rank):
                    moves.append(("reserve", 0, found_idx))
                    found_tops[found_idx] = card
                    moved = True
                    break

        if moved:
            continue

        # Check waste
        card = waste.peek()
        if card is not None:
            for found_idx, found_top in enumerate(found_tops):
                if can_place_on_foundation(card, found_top, foundation_base_rank):
                    moves.append(("waste", 0, found_idx))
                    found_tops[found_idx] = card
                    moved = True
                    break

        if moved:
            continue

        # Check tableau
        for tab_idx, tab in enumerate(tableau):
            card = tab.peek()
            if card is None:
                continue
            for found_idx, found_top in enumerate(found_tops):
                if can_place_on_foundation(card, found_top, foundation_base_rank):
                    moves.append(("tableau", tab_idx, found_idx))
                    found_tops[found_idx] = card
                    moved = True
                    break
            if moved:
                break

    return moves


def _clone_card(card: Card) -> Card:
    suit_index = Card.suitNames.index(card.suit)
    clone = Card((suit_index * 13) + card.value + 1)
    if clone.facedown != card.facedown:
        clone.flip()
    return clone


def _clone_pile(pile: Pile) -> Pile:
    clone = Pile()
    for card in pile.cards:
        clone.append(_clone_card(card))
    return clone


def _has_any_player_move(
    foundations: tuple[Pile, Pile, Pile, Pile],
    tableau: tuple[Pile, Pile, Pile, Pile],
    reserve: Pile,
    waste: Pile,
    foundation_base_rank: int,
) -> bool:
    reserve_top = reserve.peek()
    waste_top = waste.peek()
    foundation_tops = [foundation.peek() for foundation in foundations]
    tableau_tops = [pile.peek() for pile in tableau]

    # Foundation moves from reserve, waste, or tableau tops.
    for source_card in [reserve_top, waste_top, *tableau_tops]:
        if source_card is None:
            continue
        for foundation_top in foundation_tops:
            if can_place_on_foundation(
                source_card, foundation_top, foundation_base_rank
            ):
                return True

    # Tableau to tableau moves (single top card or full column).
    for src_idx, source in enumerate(tableau):
        src_top = source.peek()
        if src_top is None:
            continue

        full_column_cards = list(source.cards)
        can_move_full_column = len(full_column_cards) > 1 and is_valid_tableau_run(
            full_column_cards
        )

        for dst_idx, dest_top in enumerate(tableau_tops):
            if src_idx == dst_idx:
                continue

            if dest_top is None:
                # Empty spaces must be filled by reserve, then waste.
                continue

            if can_place_on_tableau(src_top, dest_top):
                return True
            if can_move_full_column and can_place_on_tableau(
                full_column_cards[0], dest_top
            ):
                return True

    # Reserve, waste, and foundation top cards can move to a non-empty tableau.
    extra_sources = [reserve_top, waste_top, *foundation_tops]
    for source_card in extra_sources:
        if source_card is None:
            continue
        for dest_top in tableau_tops:
            if dest_top is None:
                continue
            if can_place_on_tableau(source_card, dest_top):
                return True

    # Empty tableau spaces can only be filled by reserve top (or waste top if reserve is empty).
    has_empty_tableau = any(top is None for top in tableau_tops)
    if has_empty_tableau:
        if reserve_top is not None:
            return True
        if waste_top is not None:
            return True

    return False


def _has_move_during_stock_pass(
    stock: Pile,
    waste: Pile,
    reserve: Pile,
    foundations: tuple[Pile, Pile, Pile, Pile],
    tableau: tuple[Pile, Pile, Pile, Pile],
    foundation_base_rank: int,
) -> bool:
    sim_stock = _clone_pile(stock)
    sim_waste = _clone_pile(waste)
    sim_reserve = _clone_pile(reserve)
    sim_foundations = tuple(_clone_pile(pile) for pile in foundations)
    sim_tableau = tuple(_clone_pile(pile) for pile in tableau)

    try:
        if len(sim_stock) == 0:
            redeal_waste_to_stock(sim_stock, sim_waste)

        while len(sim_stock) > 0:
            draw_three_from_stock(sim_stock, sim_waste)
            if _has_any_player_move(
                sim_foundations,
                sim_tableau,
                sim_reserve,
                sim_waste,
                foundation_base_rank,
            ):
                return True

        return False
    finally:
        sim_stock.cards.clear()
        sim_waste.cards.clear()
        sim_reserve.cards.clear()
        for pile in sim_foundations:
            pile.cards.clear()
        for pile in sim_tableau:
            pile.cards.clear()


def is_stalemate(state: DemonState) -> bool:
    if _has_any_player_move(
        state.foundations,
        state.tableau,
        state.reserve,
        state.waste,
        state.foundation_base_rank,
    ):
        return False
    return not _has_move_during_stock_pass(
        state.stock,
        state.waste,
        state.reserve,
        state.foundations,
        state.tableau,
        state.foundation_base_rank,
    )


class DemonWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application, parent: Gtk.Window | None = None) -> None:
        super().__init__(application=app)
        self.set_title("Demon")
        self.set_default_size(980, 860)
        self.add_css_class("table-window")

        if parent is not None:
            self.set_transient_for(parent)

        self._state = create_initial_state()
        self._card_data_dir = resolve_card_data_dir()
        self._selection: Selection | None = None
        self._undo_stack: list[tuple[DemonState, bool]] = []
        self._auto_moves_enabled = True
        self._auto_moves_pending = False
        self._auto_move_generation = 0
        self._move_seen_this_round: bool = False
        self._won_this_round = False
        self._install_selection_css()
        self._stats_started, self._stats_won = record_started(GAME_ID)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.set_margin_top(18)
        root.set_margin_bottom(18)
        root.set_margin_start(18)
        root.set_margin_end(18)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        title = Gtk.Label(label="Demon")
        title.add_css_class("title-2")
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        header.append(title)

        self._deselect_button = Gtk.Button(label="Deselect")
        self._deselect_button.connect("clicked", self._on_deselect_clicked)
        self._deselect_button.set_sensitive(False)
        header.append(self._deselect_button)

        self._undo_button = Gtk.Button(label="Undo Last Move")
        self._undo_button.connect("clicked", self._on_undo_clicked)
        self._undo_button.set_sensitive(False)
        header.append(self._undo_button)

        self._auto_move_toggle = Gtk.ToggleButton(label="Auto-Move: On")
        self._auto_move_toggle.set_active(True)
        self._auto_move_toggle.connect("toggled", self._on_auto_move_toggled)
        header.append(self._auto_move_toggle)

        new_game_button = Gtk.Button(label="New Game")
        new_game_button.connect("clicked", self._on_new_game_clicked)
        header.append(new_game_button)

        root.append(header)

        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._status = Gtk.Label(
            label="Base-rank foundations, draw-3 stock, reserve fills gaps first"
        )
        self._status.add_css_class("dim-label")
        self._status.set_halign(Gtk.Align.START)
        self._status.set_hexpand(True)
        status_row.append(self._status)
        self._stats_label = Gtk.Label()
        self._stats_label.add_css_class("dim-label")
        self._stats_label.set_halign(Gtk.Align.END)
        status_row.append(self._stats_label)
        root.append(status_row)
        self._update_stats_label()

        root.append(
            build_rules_panel(
                f"Reserve: 13 cards, top card playable. Base rank: "
                f"{RANK_NAMES[self._state.foundation_base_rank]}.\n"
                "Foundations: build up by suit from the base rank, wrapping after King.\n"
                "Tableau: build down by alternating color, wrapping Ace to King.\n"
                "Moves: move a single top card or an entire tableau column.\n"
                "Empty tableau spaces must be filled from the reserve if possible; once the reserve is empty, fill from the waste.\n"
                "Stock: draw 3 to the waste with unlimited redeals."
            )
        )

        self._board = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._board.set_halign(Gtk.Align.START)
        root.append(self._board)

        self._apply_mandatory_reserve_moves()
        self._refresh_board()

        self.set_child(root)

    def _refresh_board(self) -> None:
        child = self._board.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._board.remove(child)
            child = nxt
        self._board.append(self._build_board())
        self._update_action_buttons()

    def _update_action_buttons(self) -> None:
        self._deselect_button.set_sensitive(self._selection is not None)
        self._undo_button.set_sensitive(
            bool(self._undo_stack) and not self._auto_moves_pending
        )

    def _build_board(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)

        top_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=TABLEAU_COL_GAP
        )
        top_row.append(
            build_named_pile(
                "Reserve",
                self._state.reserve,
                self._card_widget,
                on_click=self._on_reserve_clicked,
                selected=self._is_selected_named("reserve", 0),
            )
        )
        top_row.append(
            build_named_pile(
                "Stock",
                self._state.stock,
                self._card_widget,
                on_click=self._on_stock_clicked,
                selected=False,
            )
        )
        top_row.append(
            build_named_pile(
                "Waste",
                self._state.waste,
                self._card_widget,
                on_click=self._on_waste_clicked,
                selected=self._is_selected_named("waste", 0),
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
        self._cancel_auto_moves()
        self._state = create_initial_state()
        self._selection = None
        self._undo_stack.clear()
        self._move_seen_this_round = False
        self._won_this_round = False
        self._stats_started, self._stats_won = record_started(GAME_ID)
        self._update_stats_label()
        self._set_status(
            "Base-rank foundations, draw-3 stock, reserve fills gaps first"
        )
        self._apply_mandatory_reserve_moves()
        self._refresh_board()
        self._run_auto_moves_if_enabled()

    def _on_deselect_clicked(self, _button: Gtk.Button) -> None:
        self._selection = None
        self._set_status("Selection cleared")
        self._refresh_board()

    def _on_undo_clicked(self, _button: Gtk.Button) -> None:
        if not self._undo_stack or self._auto_moves_pending:
            return
        self._cancel_auto_moves()
        state, move_seen_this_round = self._undo_stack.pop()
        self._state = clone_game_state(state)
        self._move_seen_this_round = move_seen_this_round
        self._selection = None
        self._set_status("Undid last move")
        self._refresh_board()

    def _on_auto_move_toggled(self, toggle: Gtk.ToggleButton) -> None:
        self._auto_moves_enabled = toggle.get_active()
        label = "Auto-Move: On" if self._auto_moves_enabled else "Auto-Move: Off"
        toggle.set_label(label)
        if self._auto_moves_enabled:
            self._run_auto_moves_if_enabled()
        else:
            self._cancel_auto_moves()

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
            .status-error {
                color: #cc0000;
                font-weight: bold;
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
        snapshot = self._make_undo_entry()
        drew = draw_three_from_stock(self._state.stock, self._state.waste)
        if drew:
            self._undo_stack.append(snapshot)
            # Track whether this waste position has any valid move.
            if _has_any_player_move(
                self._state.foundations,
                self._state.tableau,
                self._state.reserve,
                self._state.waste,
                self._state.foundation_base_rank,
            ):
                self._move_seen_this_round = True
            self._selection = None
            self._apply_mandatory_reserve_moves()
            self._check_end_of_game()
            self._refresh_board()
            self._run_auto_moves_if_enabled()
            return

        # Stock was empty — end of a round; try to redeal.
        if len(self._state.waste) == 0:
            return  # Both stock and waste empty — nothing to do.

        # Only declare stalemate after a complete round with no valid moves seen.
        if not self._move_seen_this_round and not _has_any_player_move(
            self._state.foundations,
            self._state.tableau,
            self._state.reserve,
            self._state.waste,
            self._state.foundation_base_rank,
        ):
            self._selection = None
            self._set_status("No possible moves — game over.", error=True)
            return

        self._undo_stack.append(snapshot)
        redeal_waste_to_stock(self._state.stock, self._state.waste)
        self._move_seen_this_round = False
        self._selection = None
        self._apply_mandatory_reserve_moves()
        self._check_end_of_game()
        self._refresh_board()
        self._run_auto_moves_if_enabled()

    def _on_reserve_clicked(self) -> None:
        if len(self._state.reserve) == 0:
            self._selection = None
            return
        if self._selection and self._selection.source == "reserve":
            self._selection = None
            self._set_status("Selection cleared")
            return

        self._selection = Selection(source="reserve", pile_index=0)
        self._set_status("Selected reserve top")

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
                self._move_seen_this_round = True
                self._selection = None
                self._apply_mandatory_reserve_moves()
                self._check_end_of_game()
                self._refresh_board()
                self._run_auto_moves_if_enabled()
            return

        source = self._state.foundations[foundation_idx]
        if len(source) == 0:
            return

        self._selection = Selection(source="foundation", pile_index=foundation_idx)
        self._set_status(f"Selected foundation {foundation_idx + 1} top")

    def _on_tableau_clicked(self, tableau_idx: int, y_pos: float) -> None:
        pile = self._state.tableau[tableau_idx]

        if self._selection is not None:
            moved = self._move_selection_to_tableau(tableau_idx)
            if moved:
                self._move_seen_this_round = True
                self._selection = None
                self._apply_mandatory_reserve_moves()
                self._check_end_of_game()
                self._refresh_board()
                self._run_auto_moves_if_enabled()
            return

        clicked_index = self._tableau_card_index_from_y(pile, y_pos)
        if clicked_index is None:
            return

        if clicked_index == len(pile.cards) - 1:
            start_index = clicked_index
            self._set_status(f"Selected T{tableau_idx + 1} top card")
        else:
            start_index = 0
            self._set_status(f"Selected full column from T{tableau_idx + 1}")

        self._selection = Selection(
            source="tableau",
            pile_index=tableau_idx,
            start_index=start_index,
        )

    def _move_selection_to_foundation(self, foundation_idx: int) -> bool:
        selection = self._selection
        if selection is None:
            return False

        if not self._selection_is_single_card(selection):
            self._set_status("Only single cards can move to foundation")
            return False

        card = self._peek_selected_card(selection)
        dest = self._state.foundations[foundation_idx]
        if card is None:
            return False
        if not can_place_on_foundation(
            card, dest.peek(), self._state.foundation_base_rank
        ):
            self._set_status("Illegal move to foundation")
            return False

        self._push_undo_state()
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

        dest = self._state.tableau[tableau_idx]
        cards = self._get_selected_cards(selection)
        if not cards:
            return False

        if dest.peek() is None:
            if not self._can_fill_empty_tableau(selection):
                self._set_status(
                    "Empty tableau must be filled from reserve, then waste"
                )
                return False
        else:
            if not is_valid_tableau_run(cards):
                self._set_status("Selected cards are not a valid tableau move")
                return False
            if not can_place_on_tableau(cards[0], dest.peek()):
                self._set_status("Illegal move to tableau")
                return False

        self._push_undo_state()
        moved = self._pop_selected_cards(selection)
        for card in moved:
            dest.append(card)
        self._post_source_cleanup(selection)
        return True

    def _make_undo_entry(self) -> tuple[DemonState, bool]:
        return clone_game_state(self._state), self._move_seen_this_round

    def _push_undo_state(self) -> None:
        self._undo_stack.append(self._make_undo_entry())

    def _cancel_auto_moves(self) -> None:
        self._auto_move_generation += 1
        self._auto_moves_pending = False
        self._update_action_buttons()

    def _can_fill_empty_tableau(self, selection: Selection) -> bool:
        if len(self._state.reserve) > 0:
            return selection.source == "reserve" and self._selection_is_single_card(
                selection
            )
        return selection.source == "waste" and self._selection_is_single_card(selection)

    def _apply_mandatory_reserve_moves(self) -> None:
        changed = True
        while changed:
            changed = False

            empty_tableau = self._first_empty_tableau_index()
            if empty_tableau is not None and len(self._state.reserve) > 0:
                self._state.tableau[empty_tableau].append(self._state.reserve.pop())
                self._reveal_reserve_top()
                changed = True
                continue

            reserve_top = self._state.reserve.peek()
            if reserve_top is None:
                continue

            foundation_idx = self._find_foundation_for_card(reserve_top)
            if foundation_idx is None:
                continue

            self._state.foundations[foundation_idx].append(self._state.reserve.pop())
            self._reveal_reserve_top()
            changed = True

    def _find_foundation_for_card(self, card: Card) -> int | None:
        for idx, foundation in enumerate(self._state.foundations):
            if can_place_on_foundation(
                card, foundation.peek(), self._state.foundation_base_rank
            ):
                return idx
        return None

    def _first_empty_tableau_index(self) -> int | None:
        for idx, pile in enumerate(self._state.tableau):
            if len(pile) == 0:
                return idx
        return None

    def _reveal_reserve_top(self) -> None:
        top = self._state.reserve.peek()
        if top is not None and top.facedown:
            top.flip()

    def _peek_selected_card(self, selection: Selection) -> Card | None:
        cards = self._get_selected_cards(selection)
        return cards[0] if cards else None

    def _selection_is_single_card(self, selection: Selection) -> bool:
        cards = self._get_selected_cards(selection)
        return len(cards) == 1

    def _get_selected_cards(self, selection: Selection) -> list[Card]:
        if selection.source == "reserve":
            top = self._state.reserve.peek()
            return [top] if top is not None else []

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
        if selection.source == "reserve":
            return [self._state.reserve.pop()]

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
        if selection.source == "reserve":
            self._reveal_reserve_top()

    def _tableau_card_index_from_y(self, pile: Pile, y_pos: float) -> int | None:
        cards = pile.cards
        if not cards:
            return None

        starts: list[int] = []
        y = 0
        for _idx in range(len(cards)):
            starts.append(y)
            y += 38

        clicked = int(y_pos)
        for idx in range(len(starts) - 1, -1, -1):
            if clicked >= starts[idx]:
                return idx
        return None

    def _check_end_of_game(self) -> None:
        total = sum(len(foundation) for foundation in self._state.foundations)
        if total == 52 and not self._won_this_round:
            self._won_this_round = True
            self._stats_started, self._stats_won = record_won(GAME_ID)
            self._update_stats_label()
            self._set_status("You win!")
            return
        # Stalemate via round tracking is handled in _on_stock_clicked.
        # Here we only catch the edge case where stock and waste are both
        # empty and no moves remain (e.g. after auto-moves drain the waste).
        if (
            len(self._state.stock) == 0
            and len(self._state.waste) == 0
            and not _has_any_player_move(
                self._state.foundations,
                self._state.tableau,
                self._state.reserve,
                self._state.waste,
                self._state.foundation_base_rank,
            )
        ):
            self._set_status("No possible moves — game over.", error=True)

    def _update_stats_label(self) -> None:
        self._stats_label.set_text(f"{self._stats_won}/{self._stats_started}")

    def _start_auto_moves(self, moves: list[tuple[str, int, int]]) -> None:
        self._auto_moves_pending = bool(moves)
        self._auto_move_generation += 1
        generation = self._auto_move_generation
        self._update_action_buttons()
        self._animate_auto_moves(moves, generation)

    def _animate_auto_moves(
        self,
        moves: list[tuple[str, int, int]],
        generation: int,
    ) -> bool:
        """Apply auto-moves one at a time with a short delay between each so
        the player can see each card slide to its foundation."""
        if generation != self._auto_move_generation:
            return False
        if not moves:
            self._auto_moves_pending = False
            self._update_action_buttons()
            self._check_end_of_game()
            return False
        source, source_idx, found_idx = moves[0]

        if source == "reserve":
            card = self._state.reserve.pop()
        elif source == "waste":
            card = self._state.waste.pop()
        else:  # tableau
            card = self._state.tableau[source_idx].pop()

        self._state.foundations[found_idx].append(card)
        self._apply_mandatory_reserve_moves()
        self._refresh_board()
        GLib.timeout_add(
            440,
            lambda: self._animate_auto_moves(moves[1:], generation) or False,
        )
        return False

    def _run_auto_moves_if_enabled(self) -> None:
        if not self._auto_moves_enabled:
            self._auto_moves_pending = False
            self._update_action_buttons()
            return
        moves = _collect_auto_moves(
            self._state.foundations,
            self._state.tableau,
            self._state.reserve,
            self._state.waste,
            self._state.foundation_base_rank,
        )
        self._start_auto_moves(moves)

    def _set_status(self, message: str, *, error: bool = False) -> None:
        self._status.set_text(message)
        if error:
            self._status.add_css_class("status-error")
        else:
            self._status.remove_css_class("status-error")


def launch(parent_window: Gtk.Window) -> None:
    app = parent_window.get_application()
    if app is None:
        raise RuntimeError("Parent window has no associated GTK application.")

    game_window = DemonWindow(app=app, parent=parent_window)
    game_window.present()
