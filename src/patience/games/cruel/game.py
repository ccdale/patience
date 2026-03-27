from dataclasses import dataclass

import gi
from ccacards.card import Card
from ccacards.pack import Pack
from ccacards.pile import Pile

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from patience.ui.cards import CARD_W, build_card_widget, resolve_card_data_dir
from patience.ui.piles import TABLEAU_COL_GAP, build_named_pile

TABLEAU_COLS = 12
PILE_SIZE = 4


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CruelState:
    foundations: tuple[Pile, Pile, Pile, Pile]
    tableau: tuple[Pile, ...]  # 12 piles


def create_initial_state() -> CruelState:
    pack = Pack()
    pack.shuffle(times=3)

    foundations = tuple(Pile() for _ in range(4))
    tableau = tuple(Pile() for _ in range(TABLEAU_COLS))

    # Extract Aces first and place them on foundations.
    non_aces = []
    while len(pack) > 0:
        card = pack.deal()
        if card.facedown:
            card.flip()
        if card.value == 0:  # Ace
            foundations[len([f for f in foundations if len(f) > 0])].append(card)
        else:
            non_aces.append(card)

    # Deal remaining 48 cards into 12 piles of 4, all face-up.
    for idx, card in enumerate(non_aces):
        tableau[idx // PILE_SIZE].append(card)

    return CruelState(foundations=foundations, tableau=tuple(tableau))


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


def can_place_on_foundation(card: Card, top: Card | None) -> bool:
    if top is None:
        return card.value == 0  # Ace
    return card.suit == top.suit and card.value == top.value + 1


def can_place_on_tableau(card: Card, top: Card | None) -> bool:
    """Cruel rule: same suit, one rank lower than destination top."""
    if top is None:
        return False  # Empty piles cannot be filled freely in Cruel.
    return card.suit == top.suit and card.value == top.value - 1


def _find_foundation_for(card: Card, foundations: tuple[Pile, ...]) -> int | None:
    for idx, pile in enumerate(foundations):
        if can_place_on_foundation(card, pile.peek()):
            return idx
    return None


def _collect_auto_moves(
    foundations: tuple[Pile, ...],
    tableau: tuple[Pile, ...],
) -> list[tuple[int, int]]:
    """Simulate the auto-move cascade and return an ordered list of
    (tableau_idx, foundation_idx) pairs without modifying state."""
    found_tops: list[Card | None] = [f.peek() for f in foundations]
    tab_stacks: list[list[Card]] = [list(p.cards) for p in tableau]
    moves: list[tuple[int, int]] = []
    moved = True
    while moved:
        moved = False
        for tab_idx, tab in enumerate(tab_stacks):
            if not tab:
                continue
            top = tab[-1]
            for found_idx, found_top in enumerate(found_tops):
                if can_place_on_foundation(top, found_top):
                    tab.pop()
                    found_tops[found_idx] = top
                    moves.append((tab_idx, found_idx))
                    moved = True
                    break
            if moved:
                break
    return moves


def collect_and_redeal(tableau: tuple[Pile, ...]) -> None:
    """Gather all tableau cards left→right, top (last dealt) first within each
    pile (i.e. bottom-to-top as dealt, so the visual order is preserved on
    redeal), then re-deal into piles of 4."""
    cards: list[Card] = []
    for pile in tableau:
        # We want to redeal in the original stacking order (bottom first).
        cards.extend(pile.cards)

    for pile in tableau:
        while pile.peek() is not None:
            pile.pop()

    for idx, card in enumerate(cards):
        tableau[idx // PILE_SIZE].append(card)


# ---------------------------------------------------------------------------
# Window
# ---------------------------------------------------------------------------


@dataclass
class Selection:
    pile_index: int


class CruelWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application, parent: Gtk.Window | None = None) -> None:
        super().__init__(application=app)
        self.set_title("Cruel")
        self.set_default_size(1100, 800)

        if parent is not None:
            self.set_transient_for(parent)

        self._state = create_initial_state()
        self._card_data_dir = resolve_card_data_dir()
        self._selection: Selection | None = None
        self._install_css()

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.set_margin_top(18)
        root.set_margin_bottom(18)
        root.set_margin_start(18)
        root.set_margin_end(18)

        # Header row
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        title = Gtk.Label(label="Cruel")
        title.add_css_class("title-2")
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        header.append(title)

        redeal_btn = Gtk.Button(label="Redeal")
        redeal_btn.connect("clicked", self._on_redeal_clicked)
        header.append(redeal_btn)

        new_game_btn = Gtk.Button(label="New Game")
        new_game_btn.connect("clicked", self._on_new_game_clicked)
        header.append(new_game_btn)

        root.append(header)

        self._status = Gtk.Label(label="Same suit, one rank lower. Redeal to regroup.")
        self._status.add_css_class("dim-label")
        self._status.set_halign(Gtk.Align.START)
        root.append(self._status)

        self._board = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._board.set_halign(Gtk.Align.START)
        root.append(self._board)

        self._refresh_board()
        self.set_child(root)

    # ------------------------------------------------------------------
    # Board building
    # ------------------------------------------------------------------

    def _refresh_board(self) -> None:
        child = self._board.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._board.remove(child)
            child = nxt
        self._board.append(self._build_board_grid())

    def _build_board_grid(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)

        # Foundation row (4 piles, left-aligned)
        foundation_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=TABLEAU_COL_GAP
        )
        for idx, pile in enumerate(self._state.foundations):
            foundation_row.append(self._build_foundation_pile(idx, pile))
        outer.append(foundation_row)

        # Tableau: two rows of 6 columns each
        top_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=TABLEAU_COL_GAP
        )
        for col in range(6):
            top_row.append(self._build_tableau_col(col))
        outer.append(top_row)

        bottom_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=TABLEAU_COL_GAP
        )
        for col in range(6, 12):
            bottom_row.append(self._build_tableau_col(col))
        outer.append(bottom_row)

        return outer

    def _build_foundation_pile(self, idx: int, pile: Pile) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.set_size_request(CARD_W, -1)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        label = Gtk.Label(label=f"Foundation {idx + 1}")
        label.add_css_class("caption")
        label.set_halign(Gtk.Align.START)
        box.append(label)

        box.append(self._card_widget(pile.peek()))

        count = Gtk.Label(label=f"{len(pile)} cards")
        count.add_css_class("dim-label")
        count.add_css_class("caption")
        count.set_halign(Gtk.Align.START)
        box.append(count)

        frame.set_child(box)

        click = Gtk.GestureClick.new()
        click.connect("released", lambda *_args, i=idx: self._on_foundation_clicked(i))
        frame.add_controller(click)
        return frame

    def _build_tableau_col(self, col: int) -> Gtk.Widget:
        selected = self._selection is not None and self._selection.pile_index == col
        pile = self._state.tableau[col]
        return build_named_pile(
            f"Pile {col + 1}",
            pile,
            self._card_widget,
            on_click=lambda c=col: self._on_tableau_clicked(c, 0.0),
            selected=selected,
        )

    def _card_widget(self, card: Card | None) -> Gtk.Widget:
        return build_card_widget(card, self._card_data_dir)

    # ------------------------------------------------------------------
    # Click handlers
    # ------------------------------------------------------------------

    def _on_new_game_clicked(self, _button: Gtk.Button) -> None:
        self._state = create_initial_state()
        self._selection = None
        self._set_status("Same suit, one rank lower. Redeal to regroup.")
        self._refresh_board()

    def _on_redeal_clicked(self, _button: Gtk.Button) -> None:
        collect_and_redeal(self._state.tableau)
        self._selection = None
        self._set_status("Redealt.")
        self._refresh_board()
        moves = _collect_auto_moves(self._state.foundations, self._state.tableau)
        self._animate_auto_moves(moves)

    def _on_foundation_clicked(self, foundation_idx: int) -> None:
        if self._selection is None:
            return
        sel_pile = self._state.tableau[self._selection.pile_index]
        card = sel_pile.peek()
        if card is None:
            self._selection = None
            return
        dest = self._state.foundations[foundation_idx]
        if can_place_on_foundation(card, dest.peek()):
            dest.append(sel_pile.pop())
            self._selection = None
            self._refresh_board()
            moves = _collect_auto_moves(self._state.foundations, self._state.tableau)
            self._animate_auto_moves(moves, check_win=True)
        else:
            self._set_status("Illegal move to foundation")

    def _on_tableau_clicked(self, pile_idx: int, _y_pos: float) -> None:
        pile = self._state.tableau[pile_idx]

        if self._selection is not None:
            if self._selection.pile_index == pile_idx:
                # Deselect
                self._selection = None
                self._set_status("Selection cleared")
                self._refresh_board()
                return
            # Try to move selection top card onto this pile
            src_pile = self._state.tableau[self._selection.pile_index]
            card = src_pile.peek()
            if card is not None and can_place_on_tableau(card, pile.peek()):
                pile.append(src_pile.pop())
                self._selection = None
                self._refresh_board()
                moves = _collect_auto_moves(self._state.foundations, self._state.tableau)
                self._animate_auto_moves(moves, check_win=True)
            else:
                self._set_status("Illegal move")
            return

        if pile.peek() is None:
            return

        self._selection = Selection(pile_index=pile_idx)
        self._set_status(f"Selected pile {pile_idx + 1} top card")
        self._refresh_board()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _animate_auto_moves(
        self, moves: list[tuple[int, int]], check_win: bool = False
    ) -> None:
        """Apply auto-moves one at a time with a short delay between each so
        the player can see each card slide to its foundation."""
        if not moves:
            if check_win:
                self._check_win()
            return
        tab_idx, found_idx = moves[0]
        pile = self._state.tableau[tab_idx]
        card = pile.peek()
        if card is not None:
            self._state.foundations[found_idx].append(pile.pop())
        self._refresh_board()
        GLib.timeout_add(220, lambda: self._animate_auto_moves(moves[1:], check_win) or False)

    def _check_win(self) -> None:
        total = sum(len(f) for f in self._state.foundations)
        if total == 52:
            self._set_status("You win! 🎉")

    def _set_status(self, message: str) -> None:
        self._status.set_text(message)

    def _install_css(self) -> None:
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


def launch(parent_window: Gtk.Window) -> None:
    app = parent_window.get_application()
    if app is None:
        raise RuntimeError("Parent window has no associated GTK application.")
    game_window = CruelWindow(app=app, parent=parent_window)
    game_window.present()
