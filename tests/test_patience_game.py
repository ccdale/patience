from patience.games.patience.game import create_initial_state


def test_create_initial_state_card_counts() -> None:
    state = create_initial_state()

    tableau_lengths = [len(pile) for pile in state.tableau]
    assert tableau_lengths == [1, 2, 3, 4, 5, 6, 7]

    total_tableau = sum(tableau_lengths)
    total_foundations = sum(len(pile) for pile in state.foundations)
    total_cards = total_tableau + len(state.stock) + len(state.waste) + total_foundations

    assert len(state.stock) == 24
    assert len(state.waste) == 0
    assert total_foundations == 0
    assert total_cards == 52


def test_create_initial_state_card_orientation() -> None:
    state = create_initial_state()

    # Stock is face-down in classic Patience.
    assert all(card.facedown for card in state.stock.cards)

    for pile in state.tableau:
        cards = pile.cards
        assert cards[-1].facedown is False
        assert all(card.facedown for card in cards[:-1])
