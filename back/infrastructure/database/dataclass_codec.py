from __future__ import annotations

from dataclasses import fields, is_dataclass
from functools import cache
from types import NoneType, UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints


@cache
def init_fields(cls: type) -> tuple[tuple[str, Any], ...]:
    hints = get_type_hints(cls)
    return tuple((field.name, hints[field.name]) for field in fields(cls) if field.init)


def decode(annotation: Any, value: Any) -> Any:
    """Reconstruit récursivement une dataclass typée depuis un document JSON ; les clés inconnues sont ignorées,
    les clés absentes reprennent la valeur par défaut du champ."""
    origin = get_origin(annotation)
    if origin is list:
        (item_type,) = get_args(annotation)
        return [decode(item_type, item) for item in value or ()]
    if origin is dict:
        return dict(value or {})
    if value is None:
        return None
    if origin in (Union, UnionType):
        (inner,) = (arg for arg in get_args(annotation) if arg is not NoneType)
        return decode(inner, value)
    if is_dataclass(annotation):
        return annotation(**{name: decode(field_type, value[name]) for name, field_type in init_fields(annotation) if name in value})
    return value
