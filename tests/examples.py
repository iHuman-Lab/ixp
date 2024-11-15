from __future__ import annotations

import logging
import time
from typing import Any

from ixp.sensors.base_sensor import Sensor
from ixp.task import Task


class ExampleTask(Task):
    def __init__(self, task_config):
        super().__init__(config=task_config)

    def execute(self):
        time.sleep(100)


class ExampleSensor(Sensor):
    def __init__(self, sensor_config):
        super().__init__(config=sensor_config)
        self.create_lsl_stream()  # Create the LSL stream when the sensor is initialized

    def get_data_signature(self) -> dict[str, Any]:
        return {
            'name': self.config['sensor_id'],
            'type': 'Temperature',
            'channel_count': 1,
            'nominal_srate': 1.0,
            'channel_format': 'float32',
            'source_id': self.config['sensor_id'],
        }

    def read_data(self):
        # Simulate reading temperature data
        self.data_to_stream = [25 + (time.time() % 5)]  # Mock data
        msg = f'Read data: {self.data_to_stream}'
        logging.debug(msg)
        self.stream_data()
