"""LabRecorder-style wxPython dialog for stream selection and file naming."""
from __future__ import annotations

from collections.abc import Callable
from typing import TypeAlias

import pylsl
import wx

_app: wx.App | None = None  # keep a reference so the app is not garbage-collected

_StartCb: TypeAlias = Callable[[list[pylsl.StreamInfo], dict[str, str], str, str], None]
_StopCb: TypeAlias = Callable[[], None]


class _RecorderDialog(wx.Dialog):
    """Two-panel dialog mirroring LabRecorder's UI."""

    _STREAM_TIMEOUT = 2.0

    def __init__(
        self,
        stream_infos: list[pylsl.StreamInfo],
        default_fields: dict[str, str],
        on_start: _StartCb,
        on_stop: _StopCb,
    ):
        super().__init__(
            None,
            title='Lab Recorder',
            size=(780, 480),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._stream_infos: list[pylsl.StreamInfo] = list(stream_infos)
        self._on_start_cb = on_start
        self._on_stop_cb = on_stop
        self._is_recording = False

        outer = wx.BoxSizer(wx.VERTICAL)
        panels = wx.BoxSizer(wx.HORIZONTAL)

        # ── Left: Record from Streams ──────────────────────────────────────
        left_box = wx.StaticBox(self, label='Record from Streams')
        left_sizer = wx.StaticBoxSizer(left_box, wx.VERTICAL)

        self._stream_list = wx.CheckListBox(self, style=wx.LB_SINGLE)
        self._populate_streams()
        left_sizer.Add(self._stream_list, proportion=1, flag=wx.EXPAND | wx.ALL, border=4)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_all = wx.Button(self, label='Select All')
        self._btn_none = wx.Button(self, label='Select None')
        self._btn_update = wx.Button(self, label='Update')
        btn_row.Add(self._btn_all, 1, wx.EXPAND | wx.RIGHT, 3)
        btn_row.Add(self._btn_none, 1, wx.EXPAND | wx.RIGHT, 3)
        btn_row.Add(self._btn_update, 1, wx.EXPAND)
        left_sizer.Add(btn_row, flag=wx.EXPAND | wx.ALL, border=4)

        panels.Add(left_sizer, proportion=1, flag=wx.EXPAND | wx.ALL, border=6)

        # ── Right: Saving to ───────────────────────────────────────────────
        right_box = wx.StaticBox(self, label='Saving to...')
        right_sizer = wx.StaticBoxSizer(right_box, wx.VERTICAL)

        grid = wx.FlexGridSizer(rows=0, cols=2, vgap=10, hgap=10)
        grid.AddGrowableCol(1)

        def add_row(label: str, value: str = '') -> wx.TextCtrl:
            grid.Add(wx.StaticText(self, label=label), flag=wx.ALIGN_CENTER_VERTICAL)
            ctrl = wx.TextCtrl(self, value=value)
            grid.Add(ctrl, flag=wx.EXPAND)
            return ctrl

        self._root_ctrl        = add_row('Study Root:',         'results')
        self._task_ctrl        = add_row('Block / Task (%b):',  'experiment')
        self._participant_ctrl = add_row('Participant (%p):',   default_fields.get('subject_id', '0000'))
        self._session_ctrl     = add_row('Session (%s):',       default_fields.get('session_id', '1'))

        right_sizer.Add(grid, proportion=1, flag=wx.EXPAND | wx.ALL, border=12)
        panels.Add(right_sizer, proportion=1, flag=wx.EXPAND | wx.ALL, border=6)

        outer.Add(panels, proportion=1, flag=wx.EXPAND)

        # ── Bottom: Start / Stop / Close ───────────────────────────────────
        action_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_start = wx.Button(self, label='Start Recording')
        self._btn_stop  = wx.Button(self, label='Stop Recording')
        self._btn_close = wx.Button(self, label='Close')
        self._btn_stop.Enable(False)
        action_row.Add(self._btn_start, 1, wx.EXPAND | wx.RIGHT, 4)
        action_row.Add(self._btn_stop,  1, wx.EXPAND | wx.RIGHT, 4)
        action_row.Add(self._btn_close, 0, wx.EXPAND)
        outer.Add(action_row, flag=wx.EXPAND | wx.ALL, border=8)

        self.SetSizer(outer)

        self._btn_all.Bind(wx.EVT_BUTTON, self._on_select_all)
        self._btn_none.Bind(wx.EVT_BUTTON, self._on_select_none)
        self._btn_update.Bind(wx.EVT_BUTTON, self._on_update)
        self._btn_start.Bind(wx.EVT_BUTTON, self._on_start)
        self._btn_stop.Bind(wx.EVT_BUTTON, self._on_stop)
        self._btn_close.Bind(wx.EVT_BUTTON, self._on_close)
        self.Bind(wx.EVT_CLOSE, self._on_close)

    # ------------------------------------------------------------------

    def _populate_streams(self) -> None:
        self._stream_list.Clear()
        for info in self._stream_infos:
            label = f'{info.name()}  [{info.type()},  {info.channel_count()} ch,  {info.nominal_srate()} Hz]'
            self._stream_list.Append(label)
        for i in range(self._stream_list.GetCount()):
            self._stream_list.Check(i, True)

    def _set_inputs_enabled(self, *, enabled: bool) -> None:
        for ctrl in (
            self._stream_list,
            self._btn_all, self._btn_none, self._btn_update,
            self._root_ctrl, self._task_ctrl,
            self._participant_ctrl, self._session_ctrl,
        ):
            ctrl.Enable(enabled)

    def _on_select_all(self, _: wx.CommandEvent) -> None:
        for i in range(self._stream_list.GetCount()):
            self._stream_list.Check(i, True)

    def _on_select_none(self, _: wx.CommandEvent) -> None:
        for i in range(self._stream_list.GetCount()):
            self._stream_list.Check(i, False)

    def _on_update(self, _: wx.CommandEvent) -> None:
        self._stream_infos = pylsl.resolve_streams(self._STREAM_TIMEOUT)
        self._populate_streams()

    def _on_start(self, _: wx.CommandEvent) -> None:
        selected = [
            self._stream_infos[i]
            for i in range(self._stream_list.GetCount())
            if self._stream_list.IsChecked(i)
        ]
        info = {
            'subject_id': self._participant_ctrl.GetValue().strip(),
            'session_id': self._session_ctrl.GetValue().strip(),
        }
        self._on_start_cb(selected, info, self._root_ctrl.GetValue().strip(), self._task_ctrl.GetValue().strip())
        self._is_recording = True
        self._set_inputs_enabled(enabled=False)
        self._btn_start.Enable(False)
        self._btn_stop.Enable(True)
        self.SetTitle('Lab Recorder  \u25cf  Recording')

    def _on_stop(self, _: wx.CommandEvent) -> None:
        self._on_stop_cb()
        self._is_recording = False
        self._set_inputs_enabled(enabled=True)
        self._btn_start.Enable(True)
        self._btn_stop.Enable(False)
        self.SetTitle('Lab Recorder')

    def _on_close(self, _: wx.CommandEvent | wx.CloseEvent) -> None:
        if self._is_recording:
            self._on_stop_cb()
            self._is_recording = False
        self.EndModal(wx.ID_CANCEL)


def show_recorder_dialog(
    stream_infos: list[pylsl.StreamInfo],
    default_fields: dict[str, str] | None = None,
    *,
    on_start: _StartCb,
    on_stop: _StopCb,
) -> None:
    """
    Show the LabRecorder-style dialog with Start / Stop / Close buttons.

    Parameters
    ----------
    stream_infos : list[pylsl.StreamInfo]
        Initially discovered streams shown in the left panel.
    default_fields : dict[str, str], optional
        Default ``subject_id`` / ``session_id`` values.
    on_start : callable
        Called with ``(selected, participant_info, root, task)`` when the user
        clicks *Start Recording*.
    on_stop : callable
        Called with no arguments when the user clicks *Stop Recording* or
        closes the dialog while recording is active.

    """
    global _app  # noqa: PLW0603
    if not wx.GetApp():
        _app = wx.App(False)

    dlg = _RecorderDialog(stream_infos, default_fields or {}, on_start, on_stop)
    dlg.ShowModal()
    dlg.Destroy()
