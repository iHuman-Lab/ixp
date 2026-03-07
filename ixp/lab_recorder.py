from __future__ import annotations

import logging
import socket
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_HOST = 'localhost'
_DEFAULT_PORT = 22345


class LabRecorderClient:
    """
    Remote control client for LabRecorder via its TCP interface (RCP).

    Allows checking if LabRecorder is running, setting the output filename
    using participant metadata, and starting/stopping recording.

    Parameters
    ----------
    host : str, optional
        Hostname where LabRecorder is running. Default is 'localhost'.
    port : int, optional
        RCP port. Default is 22345.

    Examples
    --------
    >>> recorder = LabRecorderClient()
    >>> if recorder.is_running():
    ...     recorder.set_filename(subject_id='S01', session_id='1', root='results')
    ...     recorder.start()

    """

    def __init__(self, host: str = _DEFAULT_HOST, port: int = _DEFAULT_PORT):
        self.host = host
        self.port = port

    def is_running(self) -> bool:
        """
        Check whether LabRecorder is reachable on the RCP port.

        Returns
        -------
        bool
            True if LabRecorder is running and accepting connections.

        """
        try:
            with socket.create_connection((self.host, self.port), timeout=1):
                return True
        except OSError:
            return False

    def set_filename(
        self,
        subject_id: str,
        session_id: str,
        root: str = 'results',
        task: str = 'experiment',
    ) -> None:
        """
        Set the XDF output filename in LabRecorder using participant metadata.

        Follows BIDS-style naming:
        ``<root>/sub-<subject_id>/ses-<session_id>/<task>.xdf``

        Parameters
        ----------
        subject_id : str
            Participant identifier (e.g. 'S01').
        session_id : str
            Session identifier (e.g. '1').
        root : str, optional
            Root directory for recordings. Default is 'results'.
        task : str, optional
            Task label used in the filename. Default is 'experiment'.

        """
        path = Path(root) / f'sub-{subject_id}' / f'ses-{session_id}' / f'{task}.xdf'
        path.parent.mkdir(parents=True, exist_ok=True)
        self._send(f'filename {path}')
        logger.info(f'[LabRecorder] Output file set to: {path}')

    def start(self) -> None:
        """
        Start recording in LabRecorder.

        """
        self._send('start')
        logger.info('[LabRecorder] Recording started.')

    def stop(self) -> None:
        """
        Stop recording in LabRecorder.

        """
        self._send('stop')
        logger.info('[LabRecorder] Recording stopped.')

    def _send(self, command: str) -> None:
        """
        Send a raw RCP command to LabRecorder.

        Parameters
        ----------
        command : str
            Command string to send (newline appended automatically).

        Raises
        ------
        ConnectionError
            If LabRecorder is not reachable.

        """
        try:
            with socket.create_connection((self.host, self.port), timeout=2) as sock:
                sock.sendall((command + '\n').encode())
        except OSError as e:
            msg = f'Could not connect to LabRecorder at {self.host}:{self.port} — is it running?'
            raise ConnectionError(msg) from e
