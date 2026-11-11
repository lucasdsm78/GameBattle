from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

# Nom d'équipe envoyé par le client : borné ici, vérifié contre les équipes du salon par le domaine.
TeamChoice = Annotated[str, StringConstraints(min_length=1, max_length=20)]
