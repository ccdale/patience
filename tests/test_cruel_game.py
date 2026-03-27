from ccacards.card import Card
from ccacards.pile import Pile

from patience.games.cruel.game import (
    CruelState,
    can_place_on_foundation,
    can_place_on_tableau,
    collect_and_redeal,
    create_initial_state,
)


def test_initial_state_card_counts() -> None:
    state = create_initial_state()

    tableau_total = sum(len(p) for p in state.tableau)
    foundation_total = sum(len(p) for p in state.foundations)
    assert tableau_total + foundation_total == 52
    assert len(state.tableau) == 13


def test_initial_state_all_face_up() -> None:
    state = create_initial_state()
    for pile in state.tableau:
        assert all(not card.facedown for card in pile.cards)


def test_can_place_on_foundation_ace_first() -> None:
    ace_spades = Card(1)
    two_spades = Card(2)
    ace_hearts = Card(14)

    assert can_place_on_foundation(ace_spades, None) is True
    assert can_place_on_foundation(two_spades, None) is False
    assert can_place_on_foundation(two_spades, ace_spades) is True
    assert can_place_on_foundation(ace_hearts, ace_spades) is False


def test_can_place_on_tableau_same_suit_one_lower() -> None:
    # Spades: index 1=Ace, 2=Two, ..., 13=King
    king_spades = Card(13)
    queen_spades = Card(12)
    queen_hearts = Card(25)  # Hearts start at 14

    # Same suit, one rank lower → legal
    assert can_place_on_tableau(queen_spades, king_spades) is True
    # Different suit → illegal (Cruel requires same suit)
    assert can_place_on_tableau(queen_hearts, king_spades) is False
    # Empty pile → not allowed in Cruel
    assert can_place_on_tableau(king_spades, None) is False


def test_collect_and_redeal_preserves_all_cards() -> None:
    state = create_initial_state()

    before = sum(len(p) for p in state.tableau) + sum(len(p) for p in state.foundations)
    collect_and_redeal(state.tableau)
    after = sum(len(p) for p in state.tableau) + sum(len(p) for p in state.foundations)

    assert before == after


def test_collect_and_redeal_produces_piles_of_four() -> None:
    # Build a controlled 12-card tableau (3 piles of 4)
    tableau = tuple(Pile() for _ in range(3))
    for i, card_idx in enumerate(range(1, 13)):
        tableau[i // 4].append(Card(card_idx))

    collect_and_redeal(tableau)

    pile_lengths = [len(p) for p in tableau]
    assert pile_lengths == [4, 4, 4]
