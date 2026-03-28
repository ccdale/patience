from ccacards.card import Card

from patience.games.demon.game import (
    can_place_on_foundation,
    can_place_on_tableau,
    create_initial_state,
    draw_three_from_stock,
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
