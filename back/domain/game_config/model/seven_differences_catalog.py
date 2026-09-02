from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass(frozen=True, slots=True)
class SevenDifferencesPuzzle:
    id: str
    title: str
    original_image_url: str
    modified_image_url: str
    differences: tuple[tuple[str, str], ...]


PUZZLES = (
    SevenDifferencesPuzzle(
        id="stadium-night-01",
        title="Soir de finale",
        original_image_url="/seven-differences/stadium-7ca9-original.svg",
        modified_image_url="/seven-differences/stadium-f34b-modified.svg",
        differences=(
            ("score", "Le score sur le panneau est différent"),
            ("ball", "Le ballon a changé de couleur"),
            ("flag", "Le drapeau du supporter a disparu"),
            ("shirt", "Le numéro du maillot est différent"),
            ("light", "Un projecteur du stade est éteint"),
            ("cone", "Le cône orange n’est plus à côté du but"),
            ("star", "Une étoile est apparue au-dessus des tribunes"),
        ),
    ),
)


def pick_seven_differences_puzzle() -> SevenDifferencesPuzzle:
    return random.choice(PUZZLES)
