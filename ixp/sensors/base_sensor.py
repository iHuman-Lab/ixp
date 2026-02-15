from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from pylsl import StreamInfo, StreamOutlet


class Sensor(ABC):
    """
    Base class for all sensors.

    Parameters
    ----------
    config : dict[str, Any]
        Configuration dictionary containing LSL stream settings:

        - name : str - Stream name
        - type : str - Stream type
        - channel_count : int - Number of channels
        - nominal_srate : float - Nominal sampling rate
        - channel_format : str - Data format
        - source_id : str - Unique source identifier

    logger : logging.Logger, optional
        Logger instance. If None, creates one from the class module.

    Attributes
    ----------
    config : dict[str, Any]
        Configuration dictionary for the sensor.
    lsl_stream : StreamOutlet or None
        The LSL stream outlet for pushing data.
    recording : bool
        Whether the sensor is currently recording.
    logger : logging.Logger
        Logger instance for this sensor.

    """

    def __init__(self, config: dict[str, Any], logger: logging.Logger | None = None):
        self.config = config
        self.lsl_stream = None
        self.recording = True
        self.logger = logger or logging.getLogger(self.__class__.__module__)

    def create_lsl_stream(self):
        """
        Create an LSL stream for the sensor using the data signature.

        Uses the configuration dictionary to set up the LSL StreamInfo
        and create a StreamOutlet.

        """
        # Create LSL stream with the data signature
        info = StreamInfo(
            name=self.config['name'],
            type=self.config['type'],
            channel_count=self.config['channel_count'],
            nominal_srate=self.config['nominal_srate'],
            channel_format=self.config['channel_format'],
            source_id=self.config['source_id'],
        )
        self.lsl_stream = StreamOutlet(info)

    def stream_data(self, data_to_stream):
        """
        Stream data for this sensor.

        Parameters
        ----------
        data_to_stream : list[Any]
            Data sample to push to the LSL stream.

        """
        self.lsl_stream.push_sample(data_to_stream)

    @abstractmethod
    def initialize(self):
        """
        Initialize the sensor.

        This method should set up any hardware connections or resources
        needed before the sensor can start recording.

        """

    @abstractmethod
    def get_data_signature(self) -> dict[str, Any]:
        """
        Return the data signature for this sensor.

        Returns
        -------
        dict[str, Any]
            Dictionary describing the data channels and their types.

        """

    @abstractmethod
    def read_data(self):
        """
        Read data from the sensor.

        Returns
        -------
        list[Any] or None
            Data sample from the sensor, or None if no data available.

        """
