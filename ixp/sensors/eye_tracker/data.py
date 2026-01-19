from __future__ import annotations

from typing import Any

import numpy as np
from scipy.spatial import distance

from .utils import trackbox_to_psycho_norm

# Constants
TRACKBOX_OUTSIDE = (0.99, 0.99)
INVALID_GAZE = -1.0
INVALID_PUPIL = -1
DEFAULT_PUPIL = 0.0
TRACKBOX_SCALE = 1.7
MM_TO_CM = 10


def is_valid_gaze(values: tuple) -> bool:
    """
    Check if gaze values are valid.

    Parameters
    ----------
    values : tuple
        tuple of gaze values to validate.

    Returns
    -------
    bool
        True if all gaze values are valid, False otherwise.

    """
    return all(x != INVALID_GAZE for x in values)


def get_gaze_position(gaze_data: dict[str, Any]) -> tuple[float, float]:
    """
    Calculate average gaze position of both eyes.

    Parameters
    ----------
    gaze_data : dict
        Dictionary containing gaze tracking data with keys:
        - 'left_gaze_point_on_display_area'
        - 'right_gaze_point_on_display_area'

    Returns
    -------
    tuple
        (x, y) coordinates of average gaze position.
        Returns (nan, nan) if gaze is invalid.

    """
    left = gaze_data['left_gaze_point_on_display_area']
    right = gaze_data['right_gaze_point_on_display_area']
    x_vals = (left[0], right[0])
    y_vals = (left[1], right[1])

    if is_valid_gaze(x_vals) and is_valid_gaze(y_vals):
        return np.nanmean(x_vals), np.nanmean(y_vals)
    return np.nan, np.nan


def calculate_trackbox_coordinate(point: tuple, valid: int) -> tuple:
    """
    Calculate single eye position in trackbox coordinates.

    Parameters
    ----------
    point : tuple
        (x, y) coordinates of eye position.
    valid : int
        Validity flag for the eye position.
    tb2psycho_norm_function : callable
        Function to normalize trackbox coordinates.

    Returns
    -------
    tuple
        Normalized (x, y) coordinates in trackbox space.

    """
    if valid != 1:
        return TRACKBOX_OUTSIDE
    normalized = trackbox_to_psycho_norm((point[0], point[1]))
    return (-normalized[0] * TRACKBOX_SCALE, normalized[1])


def get_trackbox_position(gaze_data: dict[str, Any]) -> tuple[tuple[float, float], tuple[float, float]]:
    """
    Calculate eye positions in trackbox coordinates.

    Parameters
    ----------
    gaze_data : dict
        Dictionary containing gaze tracking data with keys:
        - 'left_gaze_origin_in_trackbox_coordinate_system'
        - 'right_gaze_origin_in_trackbox_coordinate_system'
        - 'left_gaze_origin_validity'
        - 'right_gaze_origin_validity'
    tb2psycho_norm_function : callable
        Function to normalize trackbox coordinates.

    Returns
    -------
    tuple of tuples
        ((left_x, left_y), (right_x, right_y)) positions in trackbox coordinates.

    """
    left = gaze_data['left_gaze_origin_in_trackbox_coordinate_system']
    right = gaze_data['right_gaze_origin_in_trackbox_coordinate_system']

    left_pos = calculate_trackbox_coordinate(left, gaze_data['left_gaze_origin_validity'])
    right_pos = calculate_trackbox_coordinate(right, gaze_data['right_gaze_origin_validity'])
    return left_pos, right_pos


def get_3d_position(gaze_data: dict[str, Any]) -> tuple[float, float, float]:
    """
    Calculate average 3D eye position in user coordinates.

    Parameters
    ----------
    gaze_data : dict
        Dictionary containing gaze tracking data with key:
        - 'left_gaze_origin_in_user_coordinate_system'
        - 'right_gaze_origin_in_user_coordinate_system'

    Returns
    -------
    tuple
        (x, y, z) coordinates of average eye position.
        Returns (0, 0, 0) if position is invalid.

    """
    left = gaze_data['left_gaze_origin_in_user_coordinate_system']
    right = gaze_data['right_gaze_origin_in_user_coordinate_system']

    coordinates = [(left[i], right[i]) for i in range(3)]
    if not any(np.isnan(coord).all() for coord in coordinates):
        return tuple(np.nanmean(coord) for coord in coordinates)
    return (0, 0, 0)


def get_eye_distance(gaze_data: dict[str, Any]) -> float:
    """
    Calculate average distance of eyes from tracker origin in centimeters.

    Parameters
    ----------
    gaze_data : dict
        Dictionary containing gaze tracking data for 3D position calculation.

    Returns
    -------
    float
        Distance from tracker origin in centimeters.
        Returns 0 if distance cannot be calculated.

    """
    eye_pos = get_3d_position(gaze_data)
    if sum(eye_pos) > 0:
        return distance.euclidean(np.array(eye_pos) / MM_TO_CM, (0, 0, 0))
    return 0


def get_pupil_size(gaze_data: dict[str, Any]) -> float:
    """
    Calculate average pupil size in millimeters.

    Parameters
    ----------
    gaze_data : dict
        Dictionary containing gaze tracking data with keys:
        - 'left_pupil_diameter'
        - 'right_pupil_diameter'

    Returns
    -------
    float
        Average pupil size in millimeters.
        Returns DEFAULT_PUPIL if either pupil measurement is invalid.

    """
    left = gaze_data['left_pupil_diameter']
    right = gaze_data['right_pupil_diameter']

    if INVALID_PUPIL not in (left, right):
        return np.nanmean([left, right])
    return DEFAULT_PUPIL


def get_eye_validity(gaze_data: dict[str, Any]) -> int:
    """
    Check validity of both eyes.

    Parameters
    ----------
    gaze_data : dict
        Dictionary containing gaze tracking data with keys:
        - 'left_gaze_origin_validity'
        - 'right_gaze_origin_validity'

    Returns
    -------
    int
        Validity code:
        - 3: both eyes valid
        - 2: right eye valid
        - 1: left eye valid
        - 0: no valid eyes

    """
    left_valid = gaze_data['left_gaze_origin_validity']
    right_valid = gaze_data['right_gaze_origin_validity']

    if left_valid == right_valid == 1:
        return 3
    return left_valid + (right_valid * 2)
