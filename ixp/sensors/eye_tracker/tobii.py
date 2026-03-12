from __future__ import annotations

from typing import Any

import tobii_research as tobii
from psychopy import core, visual

from ixp.sensors.base_sensor import Sensor
from ixp.sensors.eye_tracker.data import get_eye_distance, get_gaze_position, get_trackbox_position
from ixp.sensors.eye_tracker.utils import (
    detect_screen_size_mm,
    print_calibration_results,
    show_calibration_point,
)


class TobiiEyeTracker(Sensor):
    """
    Interface for Tobii eye tracking devices.

    Parameters
    ----------
    config : dict[str, Any]
        Configuration dictionary containing:
        - name: Stream name (default: 'TobiiEyeTracker')
        - type: Stream type (default: 'Gaze')
        - channel_count: Number of channels (default: 6)
        - nominal_srate: Sampling rate (default: 60)
        - channel_format: Data format (default: 'float32')
        - source_id: Unique source identifier
        - serial_string: Serial number of specific tracker (optional)

    Attributes
    ----------
    eyetracker : tobii.EyeTracker
        Connected Tobii eye tracker device
    tracking : bool
        Current tracking status
    gaze_data : dict
        Latest gaze data from the tracker

    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        default_config = {
            'name': 'TobiiEyeTracker',
            'type': 'Gaze',
            'channel_count': 6,  # left_x, left_y, left_z, right_x, right_y, right_z
            'nominal_srate': 60,
            'channel_format': 'float32',
            'source_id': 'tobii_eye_tracker',
        }
        if config:
            default_config.update(config)

        super().__init__(default_config)

        self.eyetracker = None
        self.tracking = False
        self.gaze_data: dict[str, Any] = {}
        self.win = None

    def initialize(self) -> None:
        """
        Initialize and connect to the Tobii eye tracker.

        This method is called by RemoteSensor after instantiation.

        """
        serial_string = self.config.get('serial_string')
        self.connect_to_tracker(serial_string)
        self.start_tracking()

    def get_data_signature(self) -> dict[str, Any]:
        """
        Return the data signature for the Tobii eye tracker.

        Returns
        -------
        dict[str, Any]
            Dictionary describing the data channels and their types.

        """
        return {
            'channels': [
                'left_gaze_x',
                'left_gaze_y',
                'left_gaze_z',
                'right_gaze_x',
                'right_gaze_y',
                'right_gaze_z',
            ],
            'units': 'normalized',
            'coordinate_system': 'tobii_display_area',
        }

    def read_data(self) -> list[float] | None:
        """
        Read current gaze data from the tracker.

        Returns
        -------
        list[float] or None
            List of gaze coordinates [left_x, left_y, left_z, right_x, right_y, right_z]
            or None if no data available.

        """
        if not self.gaze_data:
            return None

        left = self.gaze_data.get('left_gaze_point_3d', (0.0, 0.0, 0.0))
        right = self.gaze_data.get('right_gaze_point_3d', (0.0, 0.0, 0.0))

        # Handle None values
        if left is None:
            left = (0.0, 0.0, 0.0)
        if right is None:
            right = (0.0, 0.0, 0.0)

        return [left[0], left[1], left[2], right[0], right[1], right[2]]

    def connect_to_tracker(self, serial_string: str | None = None) -> None:
        """
        Connect to a Tobii eye tracker.

        Parameters
        ----------
        serial_string : str, optional
            Serial number of the specific tracker to connect to

        Raises
        ------
        ValueError
            If no eye trackers are found
        ConnectionError
            If connection to the tracker fails

        """
        trackers = tobii.find_all_eyetrackers()
        if not trackers:
            msg = 'No eye trackers found'
            raise ValueError(msg)

        selected_tracker = None
        if serial_string:
            selected_tracker = next((t for t in trackers if t.serial_number == serial_string), trackers[0])
        else:
            selected_tracker = trackers[0]

        try:
            self.eyetracker = tobii.EyeTracker(selected_tracker.address)
            log_msg = f'Connected to {selected_tracker.device_name} (Model: {selected_tracker.model}, S/N: {selected_tracker.serial_number})'
            self.logger.info(log_msg)
        except ConnectionError as e:
            msg = f'Failed to connect: {e}'
            raise ConnectionError(msg) from e

    def _gaze_callback(self, gaze_data: dict[str, Any]) -> None:
        """
        Store received gaze data.

        Parameters
        ----------
        gaze_data : dict[str, Any]
            Gaze data received from the tracker callback.

        """
        self.gaze_data = gaze_data

    def start_tracking(self) -> None:
        """
        Start gaze data collection.

        Raises
        ------
        ValueError
            If eye tracker is not connected

        """
        if not self.eyetracker:
            msg = 'Eye tracker not connected'
            raise ValueError(msg)

        self.eyetracker.subscribe_to(tobii.EYETRACKER_GAZE_DATA, self._gaze_callback, as_dictionary=True)
        self.tracking = True
        self.logger.info('Gaze tracking started')

    def stop_tracking(self) -> None:
        """
        Stop gaze data collection.

        Raises
        ------
        ValueError
            If eye tracker is not connected

        """
        if not self.eyetracker:
            msg = 'Eye tracker not connected'
            raise ValueError(msg)

        self.eyetracker.unsubscribe_from(tobii.EYETRACKER_GAZE_DATA, self._gaze_callback)
        self.tracking = False
        self.logger.info('Gaze tracking stopped')

    def set_display_area(
        self,
        width_mm: float | None = None,
        height_mm: float | None = None,
        mounting_offset_mm: float = 95.0,
        screen: int = 0,
    ) -> None:
        """
        Set the eye tracker's display area from physical screen dimensions.

        The display area is expressed in the tracker's User Coordinate System
        (UCS, in mm), where the origin is the tracker's optical centre, Y points
        up, and X points to the right.  This is normally configured once via
        Tobii Eye Tracker Manager, but can be set programmatically when that is
        not possible.

        When *width_mm* and *height_mm* are omitted (or ``None``), the physical
        dimensions are read automatically from the OS via ``xrandr``/``tkinter``.

        Parameters
        ----------
        width_mm : float, optional
            Physical width of the screen in millimetres.  Auto-detected if
            ``None``.
        height_mm : float, optional
            Physical height of the screen in millimetres.  Auto-detected if
            ``None``.
        mounting_offset_mm : float, optional
            Distance in mm from the tracker's optical centre to the bottom edge
            of the screen.  A value of 95 mm suits most under-bezel Tobii
            Pro/Core mounts (default: 95.0).
        screen : int, optional
            Display index used when auto-detecting dimensions (default: 0).

        Raises
        ------
        ValueError
            If the eye tracker is not connected.

        """
        if not self.eyetracker:
            msg = 'Eye tracker not connected'
            raise ValueError(msg)

        if width_mm is None or height_mm is None:
            detected_w, detected_h = detect_screen_size_mm(screen)
            width_mm = width_mm if width_mm is not None else detected_w
            height_mm = height_mm if height_mm is not None else detected_h
            self.logger.info('Auto-detected screen size: %.1f x %.1f mm', width_mm, height_mm)

        half_w = width_mm / 2.0
        top_y = mounting_offset_mm + height_mm
        display_area = tobii.DisplayArea({
            'top_left':    (-half_w, top_y,                  0.0),
            'top_right':   ( half_w, top_y,                  0.0),
            'bottom_left': (-half_w, mounting_offset_mm,     0.0),
        })
        self.eyetracker.set_display_area(display_area)
        self.logger.info(
            'Display area set: %.1f x %.1f mm, offset=%.1f mm',
            width_mm, height_mm, mounting_offset_mm,
        )

    def calibrate(self, screen: int = 1, fullscreen: bool = True) -> None:  # noqa: FBT001, FBT002
        """
        Run a 5-point screen-based calibration.

        A PsychoPy window is created for calibration if none has been set via
        :meth:`set_window`.  The window is closed afterwards only if it was
        created internally.

        Parameters
        ----------
        screen : int
            Monitor index passed to :class:`psychopy.visual.Window` when a new
            window is created (ignored when a window was set externally).
        fullscreen : bool
            Whether to open the calibration window in fullscreen mode (ignored
            when a window was set externally).

        """
        # Use an externally supplied window, or create a temporary one.
        own_win = self.win is None
        win = self.win if self.win is not None else visual.Window(
            fullscr=fullscreen,
            screen=screen,
            units='pix',
            color='black',
            checkTiming=False,
        )

        # Calibration target: outer ring shrinks toward a small inner dot to
        # pull the participant's fovea to the exact centre before sampling.
        outer_start = 40   # px - initial radius of outer ring
        outer_end   = 6    # px - final radius after animation
        animate_dur = 3.0  # s  - shrink animation duration
        hold_dur    = 0.5  # s  - static hold before collecting data
        inter_dur   = 0.5  # s  - blank gap between points

        target_outer = visual.Circle(win, radius=outer_start, fillColor='white', lineColor='white', units='pix')
        target_inner = visual.Circle(win, radius=4, fillColor='black', lineColor='black', units='pix')

        calibration = tobii.ScreenBasedCalibration(self.eyetracker)

        # Enter calibration mode.  If the display area has not been configured
        # on the device yet, attempt to derive it from the PsychoPy monitor
        # before retrying once.
        try:
            calibration.enter_calibration_mode()
        except tobii.EyeTrackerDisplayAreaNotValidError:
            self.set_display_area()
            calibration.enter_calibration_mode()

        self.logger.info(
            'Entered calibration mode for eye tracker %s',
            self.eyetracker.serial_number,
        )

        # Normalized (0-1) calibration point positions; (0,0) = top-left.
        # Points are kept 0.2 from each edge; 0.1 causes ~0.1 normalized-unit
        # accuracy loss on the Tobii Spark at extreme gaze angles.
        points_to_calibrate = [(0.5, 0.5), (0.2, 0.2), (0.2, 0.8), (0.8, 0.2), (0.8, 0.8)]

        clock = core.Clock()
        for point in points_to_calibrate:
            escaped = show_calibration_point(
                win, calibration, clock, target_outer, target_inner,
                point, outer_start, outer_end, animate_dur, hold_dur, inter_dur,
            )
            if escaped:
                if own_win:
                    win.close()
                return

        # Clear the screen while computing.
        win.flip()

        calibration_result = calibration.compute_and_apply()
        print_calibration_results(calibration_result)
        self.logger.info(
            'Calibration result: %s, collected at %d points',
            calibration_result.status,
            len(calibration_result.calibration_points),
        )

        calibration.leave_calibration_mode()
        self.logger.info('Left calibration mode')

        if own_win:
            win.close()

    def set_window(self, win: visual.Window) -> None:
        """
        Set the PsychoPy window used for calibration and validation display.

        Parameters
        ----------
        win : visual.Window
            The PsychoPy window to use.

        """
        self.win = win

    def get_trackbox_eye_pos(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """
        Return left and right eye positions in PsychoPy norm trackbox coordinates.

        Returns
        -------
        tuple of tuples
            ((left_x, left_y), (right_x, right_y)) in PsychoPy norm space.
            Returns (0.99, 0.99) for each eye when invalid or no data.

        """
        if not self.gaze_data:
            return (0.99, 0.99), (0.99, 0.99)
        return get_trackbox_position(self.gaze_data)

    def get_avg_eye_distance(self) -> float:
        """
        Return average eye distance from the tracker origin in centimeters.

        Returns
        -------
        float
            Distance in centimeters, or 0 if no data available.

        """
        if not self.gaze_data:
            return 0.0
        return get_eye_distance(self.gaze_data)

    def get_avg_gaze_pos(self) -> tuple[float, float]:
        """
        Return average gaze position in normalized display area coordinates.

        Returns
        -------
        tuple
            (x, y) gaze position, or (nan, nan) if no data available.

        """
        if not self.gaze_data:
            return (float('nan'), float('nan'))
        return get_gaze_position(self.gaze_data)

    def get_current_gaze(self) -> dict[str, Any] | None:
        """
        Get latest gaze data.

        Returns
        -------
        dict or None
            Dictionary containing gaze data for both eyes and gaze position,
            or None if no data available.

        """
        if not self.gaze_data:
            return None

        return {
            'left_eye': self.gaze_data.get('left_gaze_point_3d'),
            'right_eye': self.gaze_data.get('right_gaze_point_3d'),
            'gaze_position': self.gaze_data.get('gaze_point_on_display_area'),
        }
