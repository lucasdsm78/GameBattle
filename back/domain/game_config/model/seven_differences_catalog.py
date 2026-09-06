from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import random
import re

from domain.game_config.exception.game_config_exception import InvalidGameConfigError

CATALOG_PATH = Path(__file__).with_name("seven_differences_catalog.json")
PUZZLE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
ALLOWED_IMAGE_SUFFIXES = {".webp", ".svg"}


@dataclass(frozen=True, slots=True)
class SevenDifferencesPuzzle:
    id: str
    title: str
    original_image_url: str
    modified_image_url: str
    differences: tuple[tuple[str, str], ...]


def _validate_image_url(value: object) -> str:
    url = str(value or "")
    path = PurePosixPath(url)
    if not url.startswith("/seven-differences/") or ".." in path.parts or path.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
        raise InvalidGameConfigError("Une URL d’image des 7 différences est invalide.")
    return url


def load_seven_differences_catalog(path: Path = CATALOG_PATH) -> tuple[SevenDifferencesPuzzle, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidGameConfigError("Le catalogue des 7 différences est illisible.") from exc
    if payload.get("version") != 1 or not isinstance(payload.get("puzzles"), list):
        raise InvalidGameConfigError("La version du catalogue des 7 différences est invalide.")

    puzzles: list[SevenDifferencesPuzzle] = []
    seen_ids: set[str] = set()
    for item in payload["puzzles"]:
        puzzle_id = str(item.get("id", ""))
        title = str(item.get("title", "")).strip()
        raw_differences = item.get("differences", [])
        if not PUZZLE_ID_PATTERN.fullmatch(puzzle_id) or puzzle_id in seen_ids or not 2 <= len(title) <= 80:
            raise InvalidGameConfigError("Une entrée du catalogue des 7 différences est invalide.")
        if not isinstance(raw_differences, list) or len(raw_differences) != 7:
            raise InvalidGameConfigError("Chaque puzzle doit déclarer exactement 7 différences.")
        differences = tuple(
            (str(difference.get("id", "")), str(difference.get("label", "")).strip())
            for difference in raw_differences
        )
        if (
            {difference_id for difference_id, _ in differences} != {f"d{index:02d}" for index in range(1, 8)}
            or any(not label or len(label) > 160 for _, label in differences)
        ):
            raise InvalidGameConfigError("Les réponses d’un puzzle des 7 différences sont invalides.")
        seen_ids.add(puzzle_id)
        puzzles.append(SevenDifferencesPuzzle(
            id=puzzle_id,
            title=title,
            original_image_url=_validate_image_url(item.get("original_image_url")),
            modified_image_url=_validate_image_url(item.get("modified_image_url")),
            differences=differences,
        ))
    if not puzzles:
        raise InvalidGameConfigError("Le catalogue des 7 différences est vide.")
    return tuple(puzzles)


PUZZLES = load_seven_differences_catalog()


def pick_seven_differences_puzzle() -> SevenDifferencesPuzzle:
    return random.choice(PUZZLES)
