from __future__ import annotations

from typing import Annotated

from pydantic import ConfigDict, Field, StringConstraints

from application.shared.commands import InputModel


class CredentialsCommand(InputModel):

    model_config = ConfigDict(**{**InputModel.model_config, "str_strip_whitespace": False})

    pseudo: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=256)] = Field(repr=False)
