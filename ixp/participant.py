from __future__ import annotations

import logging
from pathlib import Path

from psychopy import gui

logger = logging.getLogger(__name__)


def _increment_suffix(suffix: str) -> str:
    """Increment a letter suffix: '' -> 'a', 'a' -> 'b', 'z' -> 'aa', 'az' -> 'ba'."""
    if not suffix:
        return 'a'
    chars = list(suffix)
    for i in range(len(chars) - 1, -1, -1):
        if chars[i] < 'z':
            chars[i] = chr(ord(chars[i]) + 1)
            return ''.join(chars)
        chars[i] = 'a'
    return 'a' + ''.join(chars)


def _next_available_session(subject_id: str, session_id: str, root: str = 'results') -> str:
    """Return the next session_id that does not already have a results folder."""
    suffix = ''
    candidate = session_id
    while (Path(root) / f'sub-{subject_id}' / f'ses-{candidate}').exists():
        suffix = _increment_suffix(suffix)
        candidate = f'{session_id}{suffix}'
    return candidate


def collect_participant_info(fields: dict[str, str] | None = None) -> dict[str, str]:
    """
    Show a GUI dialog to collect participant info before the experiment starts.

    If the results folder for the entered subject/session already exists, the
    dialog is re-shown with a suggested incremented session_id (e.g. ``1`` →
    ``1a`` → ``1b``).

    Parameters
    ----------
    fields : dict[str, str], optional
        Field names and default values shown in the dialog.
        Defaults to ``{'subject_id': '', 'session_id': '1'}``.

    Returns
    -------
    dict[str, str]
        The collected participant info (e.g. ``{'subject_id': 'S01', 'session_id': '1'}``).

    Raises
    ------
    SystemExit
        If the user cancels the dialog.

    Examples
    --------
    >>> info = collect_participant_info()
    >>> info = collect_participant_info({'subject_id': '', 'session_id': '1', 'age': ''})

    """
    fields = fields or {'subject_id': '0000', 'session_id': '1'}
    title = 'Participant Info'

    while True:
        dlg = gui.Dlg(title=title)
        for key in fields:
            dlg.addField(key + ':', fields[key])
        dlg.show()
        if not dlg.OK:
            msg = 'Experiment cancelled by user.'
            raise SystemExit(msg)

        for key, val in zip(list(fields.keys()), dlg.data):
            fields[key] = val

        subject_id = fields['subject_id']
        session_id = fields['session_id']
        next_session = _next_available_session(subject_id, session_id)

        if next_session == session_id:
            break  # No conflict

        fields['session_id'] = next_session
        title = f'Session already exists — suggested: {next_session}'

    info = dict(fields)
    logger.info('Participant info collected: %s', info)
    return info
