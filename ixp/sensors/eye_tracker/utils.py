from __future__ import annotations

import logging
import re
import subprocess
import tkinter as tk

import numpy as np
import tobii_research as tobii
from psychopy import core, event, visual

_logger = logging.getLogger(__name__)
_XY_LEN = 2


def handle_time_sync(sync_data):
    """
    Handle the time synchronization data received from the eyetracker.

    Parameters
    ----------
    sync_data : dict
        The time synchronization data received from the eyetracker.

    Returns
    -------
    dict
        The time synchronization data.

    """
    return sync_data


def subscribe_to_time_sync(eyetracker):
    """
    Subscribe to time synchronization data from the eyetracker.

    Parameters
    ----------
    eyetracker : tobii.EyeTracker
        The connected eyetracker to subscribe to time synchronization data.

    Raises
    ------
    ValueError
        If the eyetracker is not connected.

    """
    if not eyetracker:
        msg = 'Eyetracker is not connected.'
        raise ValueError(msg)

    _logger.info('Subscribing to time sync.')
    eyetracker.subscribe_to(tobii.EYETRACKER_TIME_SYNCHRONIZATION_DATA, handle_time_sync, as_dictionary=True)


def unsubscribe_from_time_sync(eyetracker):
    """
    Unsubscribe from time synchronization data from the eyetracker.

    Parameters
    ----------
    eyetracker : tobii.EyeTracker
        The connected eyetracker to unsubscribe from time synchronization data.

    """
    eyetracker.unsubscribe_from(tobii.EYETRACKER_TIME_SYNCHRONIZATION_DATA, handle_time_sync)
    _logger.info('Unsubscribed from time sync.')


def trackbox_to_active_disp(xy_coords, trackbox_coords, active_dis_coords):
    """
    Convert trackbox (mm) coordinates to normalized active display area (ADA) coordinates.

    Parameters
    ----------
    xy_coords : tuple
        A tuple (x, y) representing the trackbox coordinates.
    trackbox_coords : dict
        A dictionary containing the trackbox coordinates, including the bottom-left corner.
    active_dis_coords : dict
        A dictionary containing the ADA coordinates, including width and height.

    Returns
    -------
    tuple
        The converted ADA coordinates (x, y) in normalized units.

    Raises
    ------
    ValueError
        If `xy_coords` is not a 2-tuple, or if `trackbox_coords` or `active_dis_coords` are missing.

    """
    if not isinstance(xy_coords, tuple) or len(xy_coords) != _XY_LEN:
        msg = 'XY coordinates must be a 2-tuple.'
        raise ValueError(msg)

    if trackbox_coords is None or active_dis_coords is None:
        msg = 'Missing coordinates. Run get_tracker_space() first.'
        raise ValueError(msg)

    trackbox_low_left = trackbox_coords['bottomLeft']
    active_dis_low_left = (active_dis_coords['width'] / -2, active_dis_coords['height'] / -2)

    return (
        xy_coords[0] * trackbox_low_left[0] / active_dis_low_left[0],
        xy_coords[1] * trackbox_low_left[1] / active_dis_low_left[1],
    )


def trackbox_to_psycho_norm(xy_coords, trackbox_coords, active_dis_coords):
    """
    Convert trackbox coordinates to PsychoPy normalized window coordinates.

    Parameters
    ----------
    xy_coords : tuple
        A tuple (x, y) representing the trackbox coordinates.
    trackbox_coords : dict
        A dictionary containing the trackbox coordinates, including the bottom-left corner.
    active_dis_coords : dict
        A dictionary containing the ADA coordinates, including width and height.

    Returns
    -------
    tuple
        The converted PsychoPy normalized coordinates (x, y).

    Raises
    ------
    ValueError
        If `xy_coords` is not a 2-tuple, or if `trackbox_coords` or `active_dis_coords` are missing.

    """
    active_dis_coords = trackbox_to_active_disp(xy_coords, trackbox_coords, active_dis_coords)
    center_scale = trackbox_to_active_disp((1, 1), trackbox_coords, active_dis_coords)
    center_shift = (center_scale[0] / 2, center_scale[1] / 2)
    return (active_dis_coords[0] - center_shift[0], active_dis_coords[1] - center_shift[1])


def active_dis_to_psycho_pix(xy_coords, win):
    """
    Convert ADA coordinates to PsychoPy pixel coordinates.

    Parameters
    ----------
    xy_coords : tuple
        A tuple (x, y) representing the ADA coordinates.
    win : psychopy.visual.Window
        The PsychoPy window object used to get the screen size.

    Returns
    -------
    tuple
        The converted PsychoPy pixel coordinates (x, y).

    Raises
    ------
    ValueError
        If `xy_coords` is not a 2-tuple.

    """
    if not isinstance(xy_coords, tuple) or len(xy_coords) != _XY_LEN:
        msg = 'XY coordinates must be a 2-tuple.'
        raise ValueError(msg)

    if np.isnan(xy_coords[0]) or np.isnan(xy_coords[1]):
        return np.nan, np.nan

    mon_hw = win.size  # (width, height) in pixels
    w_shift, h_shift = mon_hw[0] / 2, mon_hw[1] / 2

    return (
        int(xy_coords[0] * mon_hw[0] - w_shift),
        int((xy_coords[1] * mon_hw[1] - h_shift) * -1),
    )


def active_disp_to_mont_pix(xy_coords, win):
    """
    Convert ADA coordinates to monitor pixel coordinates.

    Parameters
    ----------
    xy_coords : tuple
        A tuple (x, y) representing the ADA coordinates.
    win : psychopy.visual.Window
        The PsychoPy window object used to get the screen size.

    Returns
    -------
    tuple
        The converted monitor pixel coordinates (x, y).

    Raises
    ------
    ValueError
        If `xy_coords` is not a 2-tuple.

    """
    if not isinstance(xy_coords, tuple) or len(xy_coords) != _XY_LEN:
        msg = 'XY coordinates must be a 2-tuple.'
        raise ValueError(msg)

    if np.isnan(xy_coords[0]) or np.isnan(xy_coords[1]):
        return np.nan, np.nan

    return (
        int(xy_coords[0] * win.getSizePix()[0]),
        int(xy_coords[1] * win.getSizePix()[1]),
    )


def detect_screen_size_mm(screen: int = 0) -> tuple[float, float]:
    """
    Auto-detect the physical screen dimensions in millimetres.

    Tries ``xrandr`` first (Linux/X11/XWayland), then falls back to
    ``tkinter``.  Raises ``RuntimeError`` if neither succeeds.

    Parameters
    ----------
    screen : int
        Zero-based index of the connected display to query (default: 0).

    Returns
    -------
    tuple[float, float]
        ``(width_mm, height_mm)``.

    """
    # --- xrandr (Linux / XWayland) ---
    try:
        output = subprocess.check_output(
            ['xrandr'], text=True, stderr=subprocess.DEVNULL,  # noqa: S607
        )
        connected = [line for line in output.splitlines() if ' connected' in line]
        line = connected[screen] if screen < len(connected) else (connected[0] if connected else '')
        m = re.search(r'(\d+)mm x (\d+)mm', line)
        if m:
            return float(m.group(1)), float(m.group(2))
    except Exception:  # noqa: BLE001
        _logger.debug('xrandr screen size detection failed', exc_info=True)

    # --- tkinter fallback (cross-platform) ---
    try:
        root = tk.Tk()
        root.withdraw()
        w_mm = root.winfo_screenmmwidth()
        h_mm = root.winfo_screenmmheight()
        root.destroy()
        if w_mm > 0 and h_mm > 0:
            return float(w_mm), float(h_mm)
    except Exception:  # noqa: BLE001
        _logger.debug('tkinter screen size detection failed', exc_info=True)

    msg = (
        'Could not auto-detect screen physical dimensions from the OS.  '
        "Call set_display_area(width_mm, height_mm) with your screen's "
        'physical dimensions manually.'
    )
    raise RuntimeError(msg)


def show_calibration_point(  # noqa: PLR0913
    win: visual.Window,
    calibration: tobii.ScreenBasedCalibration,
    clock: core.Clock,
    target_outer: visual.Circle,
    target_inner: visual.Circle,
    point: tuple[float, float],
    outer_start: float,
    outer_end: float,
    animate_dur: float,
    hold_dur: float,
    inter_dur: float,
) -> bool:
    """
    Animate a shrinking calibration target at *point* and collect gaze data.

    Parameters
    ----------
    win : visual.Window
        PsychoPy window used for drawing.
    calibration : tobii.ScreenBasedCalibration
        Active Tobii calibration object (must already be in calibration mode).
    clock : core.Clock
        Shared clock used to drive the animation.
    target_outer : visual.Circle
        Outer ring stimulus (radius is animated).
    target_inner : visual.Circle
        Inner dot stimulus (fixed size).
    point : tuple[float, float]
        Normalised (0-1) calibration position; (0,0) = top-left.
    outer_start : float
        Initial radius of the outer ring in pixels.
    outer_end : float
        Final radius of the outer ring in pixels.
    animate_dur : float
        Duration of the shrink animation in seconds.
    hold_dur : float
        How long to hold the final target before collecting data (seconds).
    inter_dur : float
        Blank-screen duration between points (seconds).

    Returns
    -------
    bool
        ``True`` if the participant pressed Escape (calibration aborted),
        ``False`` otherwise.

    """
    pix = active_dis_to_psycho_pix(point, win)
    target_outer.pos = pix
    target_inner.pos = pix

    clock.reset()
    while clock.getTime() < animate_dur:
        t = clock.getTime() / animate_dur
        target_outer.radius = outer_start + (outer_end - outer_start) * t
        target_outer.draw()
        target_inner.draw()
        win.flip()
        if event.getKeys(['escape']):
            calibration.leave_calibration_mode()
            return True

    target_outer.radius = outer_end
    target_outer.draw()
    target_inner.draw()
    win.flip()
    core.wait(hold_dur)

    _logger.debug('Collecting calibration data at %s', point)
    if calibration.collect_data(point[0], point[1]) != tobii.CALIBRATION_STATUS_SUCCESS:
        calibration.collect_data(point[0], point[1])

    win.flip()
    core.wait(inter_dur)
    return False


def print_calibration_results(result: tobii.CalibrationResult) -> None:
    """
    Print a per-point summary of a Tobii calibration result to stdout.

    Parameters
    ----------
    result : tobii.CalibrationResult
        The result object returned by
        :meth:`tobii.ScreenBasedCalibration.compute_and_apply`.

    """
    print(f'\n=== Calibration result: {result.status} ===')  # noqa: T201
    print(f'{"Point":>12}  {"L validity":>12}  {"L pos":>18}  {"R validity":>12}  {"R pos":>18}  {"Avg pos":>18}')  # noqa: T201
    print('-' * 102)  # noqa: T201
    for cp in result.calibration_points:
        px, py = cp.position_on_display_area
        for sample in cp.calibration_samples:
            lv = sample.left_eye.validity
            rv = sample.right_eye.validity
            lx, ly = sample.left_eye.position_on_display_area
            rx, ry = sample.right_eye.position_on_display_area
            valid_xs = [v for v in (lx, rx) if not np.isnan(v)]
            valid_ys = [v for v in (ly, ry) if not np.isnan(v)]
            avg_x = sum(valid_xs) / len(valid_xs) if valid_xs else float('nan')
            avg_y = sum(valid_ys) / len(valid_ys) if valid_ys else float('nan')
            print(  # noqa: T201
                f'({px:.2f}, {py:.2f})  '
                f'{lv:>12}  ({lx:.4f}, {ly:.4f})  '
                f'{rv:>12}  ({rx:.4f}, {ry:.4f})  '
                f'({avg_x:.4f}, {avg_y:.4f})'
            )
    print('=' * 102 + '\n')  # noqa: T201
