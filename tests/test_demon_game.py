from ccacards.card import Card
from ccacards.pile import Pile

from patience.games.demon.game import (
    DemonState,
    _collect_auto_moves,
    _has_move_during_stock_pass,
    can_place_on_foundation,
    can_place_on_tableau,
    create_initial_state,
    draw_three_from_stock,
    is_stalemate,
    is_valid_tableau_run,
    redeal_waste_to_stock,
)


def test_create_initial_state_card_counts() -> None:
    state = create_initial_state()

    tableau_lengths = [len(pile) for pile in state.tableau]
    total_foundations = sum(len(pile) for pile in state.foundations)
    total_cards = (
        len(state.reserve)
        + len(state.stock)
        + len(state.waste)
        + sum(tableau_lengths)
        + total_foundations
    )

    assert len(state.reserve) == 13
    assert len(state.stock) == 34
    assert len(state.waste) == 0
    assert tableau_lengths == [1, 1, 1, 1]
    assert total_foundations == 1
    assert state.foundations[0].peek().value == state.foundation_base_rank
    assert total_cards == 52


def test_create_initial_state_card_orientation() -> None:
    state = create_initial_state()

    assert all(card.facedown for card in state.stock.cards)
    assert all(card.facedown for card in state.reserve.cards[:-1])
    assert state.reserve.peek().facedown is False
    for pile in state.tableau:
        assert pile.peek().facedown is False


def test_can_place_on_foundation_uses_base_rank_and_wraps() -> None:
    seven_spades = Card(7)
    eight_spades = Card(8)
    king_spades = Card(13)
    ace_spades = Card(1)
    seven_hearts = Card(20)

    assert can_place_on_foundation(seven_spades, None, 6) is True
    assert can_place_on_foundation(eight_spades, seven_spades, 6) is True
    assert can_place_on_foundation(ace_spades, king_spades, 6) is True
    assert can_place_on_foundation(seven_hearts, eight_spades, 6) is False


def test_can_place_on_tableau_descends_by_alternating_color_with_wrap() -> None:
    ace_hearts = Card(14)
    king_spades = Card(13)
    two_clubs = Card(41)
    ace_spades = Card(1)

    assert can_place_on_tableau(king_spades, ace_hearts) is True
    assert can_place_on_tableau(ace_hearts, two_clubs) is True
    assert can_place_on_tableau(ace_spades, two_clubs) is False
    assert can_place_on_tableau(king_spades, None) is False


def test_is_valid_tableau_run_accepts_full_wrapping_run() -> None:
    six_clubs = Card(45)
    five_hearts = Card(18)
    four_spades = Card(4)

    assert is_valid_tableau_run([six_clubs, five_hearts, four_spades]) is True


def test_stock_draw_and_redeal_round_trip_cards() -> None:
    state = create_initial_state()
    stock_before = len(state.stock)

    assert draw_three_from_stock(state.stock, state.waste) is True
    assert len(state.stock) == stock_before - 3
    assert len(state.waste) == 3
    assert all(not card.facedown for card in state.waste.cards)

    while draw_three_from_stock(state.stock, state.waste):
        pass

    assert redeal_waste_to_stock(state.stock, state.waste) is True
    assert len(state.waste) == 0
    assert len(state.stock) == stock_before
    assert all(card.facedown for card in state.stock.cards)


def test_collect_auto_moves_includes_waste_top_card() -> None:
    foundations = tuple(Pile() for _ in range(4))
    tableau = tuple(Pile() for _ in range(4))
    reserve = Pile()
    waste = Pile()

    ace_spades = Card(1)
    two_spades = Card(2)
    if ace_spades.facedown:
        ace_spades.flip()
    if two_spades.facedown:
        two_spades.flip()

    foundations[0].append(ace_spades)
    waste.append(two_spades)

    moves = _collect_auto_moves(
        foundations=foundations,
        tableau=tableau,
        reserve=reserve,
        waste=waste,
        foundation_base_rank=0,
    )

    assert moves == [("waste", 0, 0)]


def test_has_move_during_stock_pass_detects_future_waste_move() -> None:
    stock = Pile()
    waste = Pile()
    reserve = Pile()
    foundations = tuple(Pile() for _ in range(4))
    tableau = tuple(Pile() for _ in range(4))

    eight_spades = Card(8)
    seven_hearts = Card(20)
    if eight_spades.facedown:
        eight_spades.flip()

    tableau[0].append(eight_spades)
    stock.append(seven_hearts)

    assert (
        _has_move_during_stock_pass(
            stock=stock,
            waste=waste,
            reserve=reserve,
            foundations=foundations,
            tableau=tableau,
            foundation_base_rank=0,
        )
        is True
    )


def test_is_stalemate_true_when_no_moves_now_or_after_stock_pass() -> None:
    stock = Pile()
    waste = Pile()
    reserve = Pile()
    foundations = tuple(Pile() for _ in range(4))
    tableau = tuple(Pile() for _ in range(4))

    seven_hearts = Card(20)
    nine_hearts = Card(22)
    ten_hearts = Card(23)
    jack_hearts = Card(24)
    queen_hearts = Card(25)

    if nine_hearts.facedown:
        nine_hearts.flip()
    if ten_hearts.facedown:
        ten_hearts.flip()
    if jack_hearts.facedown:
        jack_hearts.flip()
    if queen_hearts.facedown:
        queen_hearts.flip()

    waste.append(seven_hearts)
    tableau[0].append(nine_hearts)
    tableau[1].append(ten_hearts)
    tableau[2].append(jack_hearts)
    tableau[3].append(queen_hearts)

    state = DemonState(
        stock=stock,
        waste=waste,
        reserve=reserve,
        foundations=foundations,
        tableau=tableau,
        foundation_base_rank=0,
    )

    assert is_stalemate(state) is True


def test_is_stalemate_false_when_move_exists_in_future_draw() -> None:
    stock = Pile()
    waste = Pile()
    reserve = Pile()
    foundations = tuple(Pile() for _ in range(4))
    tableau = tuple(Pile() for _ in range(4))

    eight_spades = Card(8)
    seven_hearts = Card(20)
    if eight_spades.facedown:
        eight_spades.flip()

    tableau[0].append(eight_spades)
    stock.append(seven_hearts)

    state = DemonState(
        stock=stock,
        waste=waste,
        reserve=reserve,
        foundations=foundations,
        tableau=tableau,
        foundation_base_rank=0,
    )

    assert is_stalemate(state) is False
