# Type validation utility
from __future__ import annotations


def validate(instance: object, base_types: tuple[type, ...]):
    if not issubclass(instance, base_types):
        msg = f'{instance} must be a subclass of {base_types}'
        raise TypeError(msg)
