from ccacards.card import Card

from patience.games.freecell.game import (
    can_place_on_foundation,
    can_place_on_tableau,
    create_initial_state,
    is_valid_tableau_run,
    max_movable_cards,
)


def test_create_initial_state_card_counts() -> None:
    state = create_initial_state()

    tableau_lengths = [len(pile) for pile in state.tableau]
    total_cards = (
        sum(tableau_lengths)
        + sum(len(pile) for pile in state.free_cells)
        + sum(len(pile) for pile in state.foundations)
    )

    assert tableau_lengths == [7, 7, 7, 7, 6, 6, 6, 6]
    assert all(len(pile) == 0 for pile in state.free_cells)
    assert all(len(pile) == 0 for pile in state.foundations)
    assert total_cards == 52


def test_create_initial_state_all_face_up() -> None:
    state = create_initial_state()
    for pile in state.tableau:
        assert all(not card.facedown for card in pile.cards)


def test_can_place_on_foundation_builds_by_suit() -> None:
    ace_spades = Card(1)
    two_spades = Card(2)
    two_hearts = Card(15)

    assert can_place_on_foundation(ace_spades, None) is True
    assert can_place_on_foundation(two_spades, ace_spades) is True
    assert can_place_on_foundation(two_hearts, ace_spades) is False


def test_can_place_on_tableau_builds_down_by_alternating_color() -> None:
    queen_hearts = Card(25)
    jack_clubs = Card(50)
    jack_diamonds = Card(24)

    assert can_place_on_tableau(jack_clubs, queen_hearts) is True
    assert can_place_on_tableau(jack_diamonds, queen_hearts) is False
    assert can_place_on_tableau(queen_hearts, None) is True


def test_is_valid_tableau_run_requires_alternating_sequence() -> None:
    queen_hearts = Card(25)
    jack_clubs = Card(50)
    ten_diamonds = Card(23)

    assert is_valid_tableau_run([queen_hearts, jack_clubs, ten_diamonds]) is True


def test_max_movable_cards_uses_free_cells_and_empty_cascades() -> None:
    assert max_movable_cards(0, 0, False) == 1
    assert max_movable_cards(2, 1, False) == 6
    assert max_movable_cards(2, 1, True) == 3
