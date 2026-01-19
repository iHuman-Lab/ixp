from __future__ import annotations

from typing import Any

import tobii_research as tobii
from psychopy import monitors, visual

from ixp.sensors.base_sensor import Sensor


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
        self._monitor = None

        # Display coordinates
        self.display_area: dict[str, tuple[float, float]] = {}
        self.trackbox: dict[str, tuple[float, float]] = {}

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
            Dictionary describing the data channels and their types

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
            or None if no data available

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

    def setup_display_area(self) -> None:
        """
        Initialize display area and trackbox coordinates.

        Raises
        ------
        ValueError
            If eye tracker is not connected

        """
        if not self.eyetracker:
            msg = 'Eye tracker not connected'
            raise ValueError(msg)

        # Get display area coordinates
        display = self.eyetracker.get_display_area()
        self.display_area = {
            'bottom_left': display.bottom_left,
            'bottom_right': display.bottom_right,
            'top_left': display.top_left,
            'top_right': display.top_right,
            'dimensions': (display.width, display.height),
        }

        # Get trackbox coordinates
        box = self.eyetracker.get_track_box()
        self.trackbox = {
            'front_bottom_left': box.front_lower_left,
            'front_bottom_right': box.front_lower_right,
            'front_top_left': box.front_upper_left,
            'front_top_right': box.front_upper_right,
            'dimensions': (
                abs(box.front_lower_right[0] - box.front_lower_left[0]),
                abs(box.front_upper_left[1] - box.front_lower_left[1]),
            ),
        }

    def setup_monitor(self, name: str | None = None, dimensions: tuple[int, int] | None = None) -> None:
        """
        Configure monitor settings.

        Parameters
        ----------
        name : str, optional
            Monitor name. Uses first available if None
        dimensions : tuple(int, int), optional
            Monitor dimensions (width, height). Uses window size if None

        Raises
        ------
        ValueError
            If no monitors are found
        TypeError
            If dimensions are not a tuple

        """
        available_monitors = monitors.getAllMonitors()
        if not available_monitors:
            msg = 'No monitors found'
            raise ValueError(msg)

        if dimensions is None:
            temp_win = visual.Window(units='pix')
            dimensions = tuple(temp_win.size)
            temp_win.close()

        if not isinstance(dimensions, tuple):
            msg = 'Dimensions must be a tuple (width, height)'
            raise TypeError(msg)

        monitor_name = name or available_monitors[0]
        monitor = monitors.Monitor(monitor_name)
        monitor.setSizePix(dimensions)
        monitor.saveMon()

        self._monitor = monitor
        log_msg = f'Monitor "{monitor_name}" configured: {dimensions!s}'
        self.logger.info(log_msg)

    def _gaze_callback(self, gaze_data: dict[str, Any]) -> None:
        """Store received gaze data."""
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

    def get_current_gaze(self) -> dict[str, Any] | None:
        """
        Get latest gaze data.

        Returns
        -------
        dict or None
            Dictionary containing gaze data for both eyes and gaze position,
            or None if no data available

        """
        if not self.gaze_data:
            return None

        return {
            'left_eye': self.gaze_data.get('left_gaze_point_3d'),
            'right_eye': self.gaze_data.get('right_gaze_point_3d'),
            'gaze_position': self.gaze_data.get('gaze_point_on_display_area'),
        }
