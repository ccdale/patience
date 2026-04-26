from ccacards.card import Card
from ccacards.pile import Pile

from patience.games.freecell.game import FreeCellState
from patience.games.undo import clone_game_state


def test_clone_game_state_creates_independent_card_and_pile_objects() -> None:
    stock = Pile()
    ace_spades = Card(1)
    if ace_spades.facedown:
        ace_spades.flip()
    stock.append(ace_spades)

    cloned_stock = clone_game_state(stock)

    assert cloned_stock is not stock
    assert cloned_stock.peek() is not ace_spades
    assert cloned_stock.peek().suit == ace_spades.suit
    assert cloned_stock.peek().value == ace_spades.value
    assert cloned_stock.peek().facedown is ace_spades.facedown

    cloned_stock.peek().flip()

    assert stock.peek().facedown is False
    assert cloned_stock.peek().facedown is True


def test_clone_game_state_restores_frozen_game_state_without_aliasing() -> None:
    free_cells = tuple(Pile() for _ in range(4))
    foundations = tuple(Pile() for _ in range(4))
    tableau = tuple(Pile() for _ in range(8))

    king_spades = Card(13)
    queen_hearts = Card(25)
    if king_spades.facedown:
        king_spades.flip()
    if queen_hearts.facedown:
        queen_hearts.flip()

    tableau[0].append(king_spades)

    state = FreeCellState(
        free_cells=free_cells,
        foundations=foundations,
        tableau=tableau,
    )
    snapshot = clone_game_state(state)

    moved = state.tableau[0].pop()
    state.tableau[1].append(moved)
    state.tableau[1].append(queen_hearts)

    restored = clone_game_state(snapshot)

    assert len(restored.tableau[0]) == 1
    assert restored.tableau[0].peek().value == 12
    assert len(restored.tableau[1]) == 0
    assert restored.tableau[0].peek() is not state.tableau[1].cards[0]
