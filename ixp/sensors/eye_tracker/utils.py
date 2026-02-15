from __future__ import annotations

import logging

import numpy as np
import tobii_research as tobii


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

    logging.info('Subscribing to time sync.')
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
    logging.info('Unsubscribed from time sync.')


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
    if not isinstance(xy_coords, tuple) or len(xy_coords) != 2:
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
    if not isinstance(xy_coords, tuple) or len(xy_coords) != 2:
        msg = 'XY coordinates must be a 2-tuple.'
        raise ValueError(msg)

    if np.isnan(xy_coords[0]) or np.isnan(xy_coords[1]):
        return np.nan, np.nan

    mon_hw = win.getSizePix()
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
    if not isinstance(xy_coords, tuple) or len(xy_coords) != 2:
        msg = 'XY coordinates must be a 2-tuple.'
        raise ValueError(msg)

    if np.isnan(xy_coords[0]) or np.isnan(xy_coords[1]):
        return np.nan, np.nan

    return (
        int(xy_coords[0] * win.getSizePix()[0]),
        int(xy_coords[1] * win.getSizePix()[1]),
    )
