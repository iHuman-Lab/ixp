# Type validation utility
from __future__ import annotations


def validate(instance: object, base_types: tuple[type, ...]):
    """
    Validate that an instance is a subclass of the specified base types.

    Parameters
    ----------
    instance : object
        The class or instance to validate.
    base_types : tuple[type, ...]
        Tuple of base types to check against.

    Raises
    ------
    TypeError
        If instance is not a subclass of any of the base types.

    """
    if not issubclass(instance, base_types):
        msg = f'{instance} must be a subclass of {base_types}'
        raise TypeError(msg)
