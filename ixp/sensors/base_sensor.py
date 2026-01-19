from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from pylsl import StreamInfo, StreamOutlet


class Sensor(ABC):
    def __init__(self, config: dict[str, Any], logger: logging.Logger | None = None):
        self.config = config
        self.lsl_stream = None
        self.recording = True
        self.logger = logger or logging.getLogger(self.__class__.__module__)

    def create_lsl_stream(self):
        """Create an LSL stream for the sensor using the data signature."""
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
        """Stream data for this sensor."""
        self.lsl_stream.push_sample(data_to_stream)

    @abstractmethod
    def initialize(self):
        """Initializes the sensor"""

    @abstractmethod
    def get_data_signature(self) -> dict[str, Any]:
        """Return the data signature for this sensor."""

    @abstractmethod
    def read_data(self):
        """Template method for reading the sensor."""
