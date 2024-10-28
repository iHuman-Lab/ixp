from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, dict

from pylsl import StreamInfo, StreamOutlet


class Sensor(ABC):
    def __init__(self, sensor_id: str, parameters: dict[str, Any]):
        self.sensor_id = sensor_id
        self.parameters = parameters
        self.lsl_stream = None
        self.data_to_stream = None

    def create_lsl_stream(self):
        """Create an LSL stream for the sensor using the data signature."""
        data_signature = self.get_data_signature()
        num_channels = data_signature['channel_count']

        # Create LSL stream with the data signature
        info = StreamInfo(
            name=data_signature['name'],
            type=data_signature['type'],
            channel_count=num_channels,
            nominal_srate=data_signature['nominal_srate'],
            channel_format=data_signature['channel_format'],
            source_id=data_signature['source_id'],
        )
        self.lsl_stream = StreamOutlet(info)

    def stream_data(self):
        """Stream data for this sensor."""
        self.lsl_stream.push_sample(self.data_to_stream)

    @abstractmethod
    def get_data_signature(self) -> dict[str, Any]:
        """Return the data signature for this sensor."""

    @abstractmethod
    def read_data(self):
        """Template method for reading the sensor."""
