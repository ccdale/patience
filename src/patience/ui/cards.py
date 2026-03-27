from pathlib import Path

import gi
from ccacards.card import Card

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk  # noqa: E402

CARD_W = 90
CARD_H = 126  # proportional to natural 537×750 px


def resolve_card_data_dir() -> Path:
    return Path(Card(1).imagefile).parent


def resolve_card_image_path(card: Card | None, card_data_dir: Path) -> Path | None:
    if card is None:
        image_path = card_data_dir / "0.png"
    elif card.facedown:
        image_path = card_data_dir / "back.png"
    else:
        image_path = card.imagefile

    return image_path if image_path.is_file() else None


def build_card_widget(card: Card | None, card_data_dir: Path) -> Gtk.Widget:
    image_path = resolve_card_image_path(card, card_data_dir)
    if image_path is not None:
        picture = Gtk.Picture.new_for_filename(str(image_path))
        picture.set_size_request(CARD_W, CARD_H)
        picture.set_content_fit(Gtk.ContentFit.FILL)
        return picture

    fallback = Gtk.Box()
    fallback.set_size_request(CARD_W, CARD_H)
    fallback.add_css_class("card")
    fallback.add_css_class("frame")
    label = Gtk.Label(label="Empty" if card is None else str(card))
    label.set_wrap(True)
    fallback.append(label)
    return fallback
