from dataclasses import fields, is_dataclass
from typing import Any, TypeVar, cast

from ccacards.card import Card
from ccacards.pile import Pile

StateT = TypeVar("StateT")


def clone_game_state(state: StateT) -> StateT:
    return cast(StateT, _clone_value(state))


def _clone_value(value: Any) -> Any:
    if isinstance(value, Card):
        return _clone_card(value)

    if isinstance(value, Pile):
        return _clone_pile(value)

    if is_dataclass(value):
        cloned_fields = {
            field.name: _clone_value(getattr(value, field.name))
            for field in fields(value)
        }
        return type(value)(**cloned_fields)

    if isinstance(value, tuple):
        return tuple(_clone_value(item) for item in value)

    if isinstance(value, list):
        return [_clone_value(item) for item in value]

    return value


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
