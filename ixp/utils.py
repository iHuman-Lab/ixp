# Type validation utility
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .task import LSLTrial


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


class StreamGuard:
    def __init__(self, trial: LSLTrial):
        self.trial = trial

    def __enter__(self):
        # Reset intent/effect counters
        self.trial._stream_called = False  # noqa: SLF001
        self.trial._samples_pushed = 0  # noqa: SLF001
        return self.trial

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.trial.stream_was_called:
            msg = f'LSLTrial "{self.trial.trial_id}": execute() did not call stream()'
            raise RuntimeError(msg)
        if not self.trial.has_streamed:
            msg = (
                f'LSLTrial "{self.trial.trial_id}": stream() was called, but no samples were pushed. Check read_data().'
            )
            raise RuntimeError(msg)
