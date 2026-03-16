"""Unified LSL recorder — delegates to LabRecorder via TCP or records in-process."""

from __future__ import annotations

import logging
import socket
import struct
import threading
from dataclasses import dataclass
from pathlib import Path

import pylsl

from .gui import show_recorder_dialog
from .xdf import (
    TAG_CLOCK_OFFSET,
    TAG_FILE_HEADER,
    TAG_SAMPLES,
    TAG_STREAM_FOOTER,
    TAG_STREAM_HEADER,
    pack_samples,
    stream_header_xml,
    write_chunk,
)

logger = logging.getLogger(__name__)

_DEFAULT_HOST = 'localhost'
_DEFAULT_PORT = 22345


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


@dataclass
class _StreamStats:
    first_timestamp: float | None = None
    last_timestamp: float | None = None
    sample_count: int = 0


def _rcp_available(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _rcp_send(host: str, port: int, command: str) -> None:
    try:
        with socket.create_connection((host, port), timeout=2) as sock:
            sock.sendall((command + '\n').encode())
    except OSError as e:
        msg = f'Could not connect to LabRecorder at {host}:{port} — is it running?'
        raise ConnectionError(msg) from e


class Recorder:
    """
    LSL recorder that auto-selects the best available backend.

    If LabRecorder is reachable on its RCP port, all commands are forwarded to
    it via TCP.  Otherwise, streams are recorded in-process using pylsl and
    written directly to XDF.

    Parameters
    ----------
    host : str, optional
        LabRecorder hostname. Default ``'localhost'``.
    port : int, optional
        LabRecorder RCP port. Default ``22345``.
    stream_timeout : float, optional
        Seconds to wait when resolving LSL streams. Default ``2.0``.
    clock_interval : float, optional
        Seconds between clock-offset measurements (in-process only). Default ``5.0``.

    Examples
    --------
    >>> recorder = Recorder()
    >>> recorder.set_filename(subject_id='S01', session_id='1')
    >>> recorder.start()       # shows stream-selection dialog if recording in-process
    >>> # ... run experiment ...
    >>> recorder.stop()

    """

    def __init__(
        self,
        host: str = _DEFAULT_HOST,
        port: int = _DEFAULT_PORT,
        stream_timeout: float = 2.0,
        clock_interval: float = 5.0,
    ):
        self._host = host
        self._port = port
        self._stream_timeout = stream_timeout
        self._clock_interval = clock_interval

        self.participant_info: dict[str, str] = {}

        self._filepath: Path | None = None
        self._recording: bool = False
        self._use_rcp: bool = False

        # In-process recording state
        self._file = None
        self._lock = threading.Lock()
        self._workers: list[tuple[threading.Thread, pylsl.StreamInlet, int, _StreamStats]] = []

    def is_running(self) -> bool:
        """Return True if recording is active."""
        return self._recording

    @property
    def save_dir(self) -> Path | None:
        """Directory where the current XDF file is being saved, or None if not started."""
        return self._filepath.parent if self._filepath else None

    def start(self) -> None:
        """
        Discover LSL streams, show the recorder dialog, then begin recording.

        The dialog (mirroring LabRecorder's UI) lets the user select streams
        and set participant info / file-naming fields.  After the dialog,
        recording is delegated to LabRecorder via RCP if reachable, otherwise
        handled in-process.

        Raises
        ------
        SystemExit
            If the user cancels the dialog.

        """
        if self._recording:
            return

        logger.info('[Recorder] Discovering LSL streams (timeout=%.1fs)...', self._stream_timeout)
        all_streams = pylsl.resolve_streams(self._stream_timeout)

        def _on_start(
            selected: list[pylsl.StreamInfo],
            info: dict[str, str],
            root: str,
            task: str,
        ) -> None:
            self.participant_info = info
            subject_id = info['subject_id']
            session_id = info['session_id']
            self._filepath = Path(root) / f'sub-{subject_id}' / f'ses-{session_id}' / f'{task}.xdf'
            self._filepath.parent.mkdir(parents=True, exist_ok=True)
            logger.info('[Recorder] Output file: %s', self._filepath)
            if _rcp_available(self._host, self._port):
                self._use_rcp = True
                _rcp_send(self._host, self._port, f'filename {self._filepath}')
                _rcp_send(self._host, self._port, 'start')
                logger.info('[Recorder] Delegating to LabRecorder (RCP).')
            else:
                self._use_rcp = False
                self._start_inprocess(selected)
            self._recording = True

        show_recorder_dialog(
            all_streams,
            self.participant_info or None,
            on_start=_on_start,
            on_stop=self.stop,
        )

    def stop(self) -> None:
        """Stop recording and finalise the XDF file."""
        if not self._recording:
            return
        self._recording = False

        if self._use_rcp:
            _rcp_send(self._host, self._port, 'stop')
            logger.info('[Recorder] LabRecorder stopped.')
        else:
            self._stop_inprocess()

    def _start_inprocess(self, stream_infos: list[pylsl.StreamInfo]) -> None:
        if not stream_infos:
            logger.warning('[Recorder] No streams selected — nothing to record.')
            return

        self._file = self._filepath.open('wb')
        self._file.write(b'XDF:')
        write_chunk(self._file, TAG_FILE_HEADER, b'<info><version>1.0</version></info>')

        for stream_id, info in enumerate(stream_infos, start=1):
            inlet = pylsl.StreamInlet(info, max_buflen=360, recover=True)
            inlet.open_stream()
            write_chunk(
                self._file,
                TAG_STREAM_HEADER,
                struct.pack('<I', stream_id) + stream_header_xml(info, stream_id).encode(),
            )
            stats = _StreamStats()
            t = threading.Thread(
                target=self._record_stream,
                args=(inlet, stream_id, info.channel_format(), stats),
                daemon=True,
                name=f'recorder-{info.name()}',
            )
            self._workers.append((t, inlet, stream_id, stats))
            t.start()
            logger.info('[Recorder] → %s (%s)', info.name(), info.type())

        logger.info('[Recorder] In-process recording started.')

    def _stop_inprocess(self) -> None:
        for t, inlet, stream_id, stats in self._workers:
            t.join(timeout=3.0)
            footer_xml = (
                f'<info>'
                f'<first_timestamp>{stats.first_timestamp or 0}</first_timestamp>'
                f'<last_timestamp>{stats.last_timestamp or 0}</last_timestamp>'
                f'<sample_count>{stats.sample_count}</sample_count>'
                f'</info>'
            )
            with self._lock:
                write_chunk(
                    self._file,
                    TAG_STREAM_FOOTER,
                    struct.pack('<I', stream_id) + footer_xml.encode(),
                )
            inlet.close_stream()

        self._workers.clear()
        self._file.close()
        self._file = None
        logger.info('[Recorder] In-process recording stopped → %s', self._filepath)

    def _record_stream(
        self,
        inlet: pylsl.StreamInlet,
        stream_id: int,
        fmt: int,
        stats: _StreamStats,
    ) -> None:
        clock_timer = 0.0
        while self._recording:
            samples, timestamps = inlet.pull_chunk(timeout=0.1, max_samples=512)
            if not timestamps:
                continue

            stats.sample_count += len(timestamps)
            if stats.first_timestamp is None:
                stats.first_timestamp = timestamps[0]
            stats.last_timestamp = timestamps[-1]

            payload = struct.pack('<I', stream_id) + pack_samples(samples, timestamps, fmt)
            with self._lock:
                if not self._file:
                    break
                write_chunk(self._file, TAG_SAMPLES, payload)

                clock_timer += timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0.0
                if clock_timer >= self._clock_interval:
                    clock_timer = 0.0
                    try:
                        collection_time = pylsl.local_clock()
                        offset = inlet.time_correction(timeout=0.5)
                        write_chunk(
                            self._file,
                            TAG_CLOCK_OFFSET,
                            struct.pack('<I', stream_id) + struct.pack('<dd', collection_time, offset),
                        )
                    except pylsl.LostError:
                        pass
