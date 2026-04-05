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
    assert len(state.tableau) == 12
    # 4 Aces placed on foundations at start
    assert foundation_total == 4
    # 48 remaining cards in 12 piles of 4
    assert tableau_total == 48


def test_initial_state_all_face_up() -> None:
    state = create_initial_state()
    for pile in state.tableau:
        assert all(not card.facedown for card in pile.cards)


def test_initial_state_aces_on_foundations() -> None:
    state = create_initial_state()
    # Every foundation starts with exactly one Ace
    for foundation in state.foundations:
        assert len(foundation) == 1
        assert foundation.peek().value == 0  # Ace
    # No Aces remain in tableau
    for pile in state.tableau:
        for card in pile.cards:
            assert card.value != 0


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


def test_collect_and_redeal_keeps_tableau0_top_as_first_redeal_top() -> None:
    tableau = tuple(Pile() for _ in range(3))

    # Pile 0 has more than 4 cards. Card 6 is the visible top before redeal.
    top_before_redeal = Card(6)
    for card_idx in range(1, 7):
        tableau[0].append(top_before_redeal if card_idx == 6 else Card(card_idx))

    # Extra cards in following piles ensure the first redeal block is meaningful.
    for card_idx in range(7, 11):
        tableau[1].append(Card(card_idx))

    collect_and_redeal(tableau)

    assert tableau[0].peek() is top_before_redeal
    assert len(tableau[0]) == 4


def test_collect_and_redeal_preserves_pickup_order_across_all_piles() -> None:
    tableau = tuple(Pile() for _ in range(3))

    c1 = Card(1)
    c2 = Card(2)
    c3 = Card(3)
    c4 = Card(4)
    c5 = Card(5)
    c6 = Card(6)
    c7 = Card(7)
    c8 = Card(8)
    c9 = Card(9)
    c10 = Card(10)

    # bottom->top in each pile at setup
    for card in (c1, c2, c3, c4, c5):
        tableau[0].append(card)
    for card in (c6, c7, c8):
        tableau[1].append(card)
    for card in (c9, c10):
        tableau[2].append(card)

    # Pickup order is: 5,4,3,2,1,8,7,6,10,9
    collect_and_redeal(tableau)

    # After redeal in groups of 4 with first-picked card on top of each group:
    # pile 0 bottom->top: 2,3,4,5
    # pile 1 bottom->top: 6,7,8,1
    # pile 2 bottom->top: 9,10
    assert list(tableau[0].cards) == [c2, c3, c4, c5]
    assert list(tableau[1].cards) == [c6, c7, c8, c1]
    assert list(tableau[2].cards) == [c9, c10]
