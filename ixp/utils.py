# Type validation utility
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

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


def save_task_results(task_name: str, results: list[dict], participant_info: dict[str, str]) -> None:
    """
    Save task results to a CSV file organised by participant and session.

    Output path: ``results/sub-<subject_id>/ses-<session_id>/<task_name>.csv``

    Parameters
    ----------
    task_name : str
        Name of the task (used as the filename).
    results : list[dict]
        List of row dicts where keys are column headers.
    participant_info : dict[str, str]
        Must contain ``subject_id`` and ``session_id``.

    """
    subject_id = participant_info.get('subject_id', 'unknown')
    session_id = participant_info.get('session_id', '1')
    path = Path('results') / f'sub-{subject_id}' / f'ses-{session_id}' / f'{task_name}.csv'
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    logger.info('Results saved to %s', path)


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
