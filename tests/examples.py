from __future__ import annotations

import logging
import time
from typing import Any

from ixp.sensors.base_sensor import Sensor
from ixp.task import GeneralTask

logger = logging.getLogger()


class ExampleTask(GeneralTask):
    def __init__(self, task_config):
        super().__init__(config=task_config)

    def execute(self):
        time.sleep(10)


class ExampleSensor(Sensor):
    def __init__(self, sensor_config):
        super().__init__(config=sensor_config)

    def get_data_signature(self) -> dict[str, Any]:
        return self.config

    def read_data(self):
        return [25]  # Mock data
