# Type validation utility
from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

_RESULTS_ROOT = Path('results')


def _next_subject_id() -> str:
    """Return the next zero-padded subject ID based on existing sub-* folders."""
    if not _RESULTS_ROOT.exists():
        return '001'
    existing = [
        int(p.name[4:])
        for p in _RESULTS_ROOT.iterdir()
        if p.is_dir() and p.name.startswith('sub-') and p.name[4:].isdigit()
    ]
    return f'{(max(existing) + 1) if existing else 1:03d}'

if TYPE_CHECKING:
    from .task import LSLTrial


def save_task_results(task_name: str, results: list[dict]) -> None:
    """
    Save task results to a timestamped CSV under an auto-indexed subject folder.

    Output path: ``results/sub-<NNN>/sub-<NNN>_<task_name>_<YYYYMMDD_HHMMSS>.csv``

    Parameters
    ----------
    task_name : str
        Name of the task.
    results : list[dict]
        List of row dicts where keys are column headers.

    """
    subject_id = _next_subject_id()
    timestamp = datetime.now(tz=timezone.utc).strftime('%Y%m%d_%H%M%S')
    filename = f'sub-{subject_id}_{task_name}_{timestamp}.csv'
    path = _RESULTS_ROOT / f'sub-{subject_id}' / filename
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
