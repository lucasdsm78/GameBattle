from __future__ import annotations

from typing import Annotated, Literal

from pydantic import StringConstraints

CultureDifficulty = Literal["toutes", "facile", "moyen", "difficile"]
TeamName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=40)]
Slug = Annotated[str, StringConstraints(min_length=1, max_length=60, pattern=r"^[a-z0-9_-]+$")]
