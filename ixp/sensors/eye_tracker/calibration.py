from __future__ import annotations

import logging

import numpy as np
from psychopy import core, event, visual

# Constants
COLORS = {
    'correct': [-1.0, 1.0, -1.0],  # Green
    'medium': [1.0, 1.0, 0.0],  # Yellow
    'wrong': [1.0, -1.0, -1.0],  # Red
    'white': [1.0, 1.0, 1.0],  # Default message color
    'black': [0.0, 0.0, 0.0],  # Default background
}

WINDOW_CONFIG = {
    'eye_radius': 0.07,
    'invalid_pos': 0.99,
    'text_height': 0.07,
    'unit': 'norm',
    'line_width': 3,
    'max_gaze_positions': 6,
    'rect_scale': (1, 1),
}

DISTANCE_RANGES = {
    'correct': (55, 75),  # Correct range (min, max)
    'medium': [(45, 54), (76, 85)],  # Medium ranges (min, max) for both low and high
}


def validate_window(psycho_win: visual.Window) -> None:
    """
    Check if PsychoPy window exists.

    Parameters
    ----------
    psycho_win : visual.Window
        The PsychoPy window to validate.

    Raises
    ------
    ValueError
        If the window is None.

    """
    if psycho_win is None:
        msg = 'No PsychoPy window available. Try calling run_trackbox() instead.'
        raise ValueError(msg)


def create_visual_elements(psycho_win: visual.Window, rect_scale: tuple[float, float]):
    """Create all visual elements needed for eye tracking."""

    # Create viewing area
    eye_area = visual.Rect(
        psycho_win,
        fillColor=COLORS['black'],
        lineColor=COLORS['black'],
        pos=[0.0, 0.0],
        units=WINDOW_CONFIG['unit'],
        lineWidth=WINDOW_CONFIG['line_width'],
        width=rect_scale[0],
        height=rect_scale[1],
    )

    # Create eye stimuli
    left_eye = visual.Circle(
        psycho_win, fillColor=eye_area.fillColor, units=WINDOW_CONFIG['unit'], radius=WINDOW_CONFIG['eye_radius']
    )
    right_eye = visual.Circle(
        psycho_win, fillColor=eye_area.fillColor, units=WINDOW_CONFIG['unit'], radius=WINDOW_CONFIG['eye_radius']
    )

    # Create message display
    message = visual.TextStim(
        psycho_win,
        text=' ',
        color=COLORS['white'],
        units=WINDOW_CONFIG['unit'],
        pos=[0.0, -0.65],
        height=WINDOW_CONFIG['text_height'],
    )

    return eye_area, left_eye, right_eye, message


def get_eye_color(eye_distance: float) -> list[float]:
    """
    Determine eye stimulus color based on distance.

    Parameters
    ----------
    eye_distance : float
        Distance of eyes from the screen in centimeters.

    Returns
    -------
    list[float]
        RGB color values in PsychoPy format [-1, 1].

    """
    # Check for 'correct' distance range
    if DISTANCE_RANGES['correct'][0] <= eye_distance <= DISTANCE_RANGES['correct'][1]:
        return COLORS['correct']

    # Check for 'medium' distance range (either of the two sub-ranges)
    for min_dist, max_dist in DISTANCE_RANGES['medium']:
        if min_dist <= eye_distance <= max_dist:
            return COLORS['medium']

    # Default to 'wrong' color
    return COLORS['wrong']


def update_eye_stimuli(left_eye: visual.Circle, right_eye: visual.Circle, eye_distance: float, window_color) -> None:
    """
    Update eye stimuli colors and handle invalid positions.

    Parameters
    ----------
    left_eye : visual.Circle
        Left eye visual stimulus.
    right_eye : visual.Circle
        Right eye visual stimulus.
    eye_distance : float
        Distance of eyes from the screen in centimeters.
    window_color : any
        Background color to use for invalid positions.

    """
    color = get_eye_color(eye_distance)

    for eye in (left_eye, right_eye):
        eye.fillColor = color
        eye.lineColor = color
        if eye.pos[0] == WINDOW_CONFIG['invalid_pos']:
            eye.fillColor = window_color
            eye.lineColor = window_color


def handle_user_input(psycho_win: visual.Window, stop_gaze_data) -> bool:
    """
    Handle user keyboard input.

    Parameters
    ----------
    psycho_win : visual.Window
        The PsychoPy window.
    stop_gaze_data : callable
        Function to call to stop gaze data collection.

    Returns
    -------
    bool
        True if 'c' was pressed to continue, False otherwise.

    Raises
    ------
    KeyboardInterrupt
        If 'q' was pressed to quit.

    """
    keys = event.getKeys(keyList=['q', 'c'])
    if 'q' in keys:
        cleanup(psycho_win, stop_gaze_data)
        msg = 'Script aborted manually.'
        raise KeyboardInterrupt(msg)
    elif 'c' in keys:  # noqa: RET506
        logging.info('Proceeding to calibration.')
        stop_gaze_data()
        psycho_win.flip()
        return True
    return False


def cleanup(psycho_win: visual.Window, stop_gaze_data) -> None:
    """
    Clean up resources.

    Parameters
    ----------
    psycho_win : visual.Window
        The PsychoPy window to close.
    stop_gaze_data : callable
        Function to call to stop gaze data collection.

    """
    stop_gaze_data()
    psycho_win.close()
    core.quit()


def draw_eye_positions(tracker, psycho_win: visual.Window):
    """
    Main function for drawing eye positions.

    Displays a real-time view of eye positions in the trackbox
    and provides feedback on viewing distance.

    Parameters
    ----------
    tracker : object
        Eye tracker object with trackboxEyePos() and getAvgEyeDist() methods.
    psycho_win : visual.Window
        The PsychoPy window to draw in.

    """
    validate_window(psycho_win)

    # Create visual elements
    rect_scale = tracker.tb2Ada(WINDOW_CONFIG['rect_scale'])
    eye_area, left_eye, right_eye, message = create_visual_elements(psycho_win, rect_scale)

    

    while True:
        # Update eye positions and distance
        left_eye.pos, right_eye.pos = tracker.trackboxEyePos()
        eye_distance = tracker.getAvgEyeDist()

        # Update visual elements
        update_eye_stimuli(left_eye, right_eye, eye_distance, psycho_win.color)
        message.text = (
            f"You're currently {int(eye_distance)} cm away from the screen.\n Press 'c' to calibrate or 'q' to abort."
        )

        # Draw frame
        for element in (eye_area, left_eye, right_eye, message):
            element.draw()
        psycho_win.flip()

        # Handle user input
        if handle_user_input(psycho_win, tracker.stopGazeData):
            return
        event.clearEvents(eventType='keyboard')


def get_default_validation_points() -> dict[str, tuple[float, float]]:
    """
    Get default 5-point validation configuration.

    Returns
    -------
    dict[str, tuple[float, float]]
        Dictionary mapping point names to (x, y) coordinates in normalized space.

    """
    return {'1': (0.1, 0.1), '2': (0.9, 0.1), '3': (0.5, 0.5), '4': (0.1, 0.9), '5': (0.9, 0.9)}


def run_validation(tracker, point_dict: dict | None = None):
    """
    Run validation after calibration.

    Displays validation points and current gaze position to verify
    calibration accuracy.

    Parameters
    ----------
    tracker : object
        Eye tracker object with validation methods.
    point_dict : dict, optional
        Dictionary mapping point names to (x, y) coordinates.
        If None, uses default 5-point configuration.

    Raises
    ------
    ValueError
        If no experimental monitor is specified.
    TypeError
        If point_dict is not a dictionary.

    """
    if tracker.win is None:
        msg = 'No experimental monitor specified. Try running set_monitor().'
        raise ValueError(msg)

    if point_dict is None:
        logging.info('Using 5-point default validation.')
        point_dict = get_default_validation_points()
    elif not isinstance(point_dict, dict):
        msg = 'point_dict must be a dictionary with number keys and coordinate values.'
        raise TypeError(msg)

    # Initialize validation
    tracker.startGazeData()
    core.wait(0.5)

    # Convert validation points
    point_positions = [tracker.ada2PsychoPix(pos) for pos in point_dict.values()]

    # Create validation stimuli
    gaze_stim = visual.Circle(
        tracker.win, radius=WINDOW_CONFIG['eye_radius'], fillColor=COLORS['correct'], units=WINDOW_CONFIG['unit']
    )

    point_stim = visual.Circle(
        tracker.win, radius=WINDOW_CONFIG['eye_radius'] / 2, fillColor=COLORS['white'], units=WINDOW_CONFIG['unit']
    )

    message = visual.TextStim(
        tracker.win,
        text="Press 'q' to quit or 'c' to continue",
        color=COLORS['white'],
        pos=[0, -0.8],
        units=WINDOW_CONFIG['unit'],
    )

    # Initialize gaze position tracking
    gaze_positions = np.array([0.0, 0.0])

    while True:
        # Update and smooth gaze positions
        gaze_positions = np.vstack((gaze_positions, np.array(tracker.getAvgGazePos())))
        if len(gaze_positions) == WINDOW_CONFIG['max_gaze_positions']:
            gaze_positions = np.delete(gaze_positions, 0, axis=0)

        current_pos = np.nanmean(gaze_positions, axis=0)
        draw_pos = tracker.ada2PsychoPix(tuple(current_pos))

        # Draw current gaze position if valid
        if draw_pos[0] != tracker.win.getSizePix()[0]:
            gaze_stim.pos = draw_pos
            gaze_stim.draw()

        # Draw validation points and message
        for pos in point_positions:
            point_stim.pos = pos
            point_stim.draw()
        message.draw()

        tracker.win.flip()

        # Handle user input
        if handle_user_input(tracker.win, tracker.stopGazeData):
            return

        event.clearEvents(eventType='keyboard')
