from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import ray
import yaml

from .sensor import Sensor
from .task import Task


@dataclass
class TaskEntry:
    order: int
    name: str
    remote_class: object  # The Ray remote class


class ExperimentRunner:
    def __init__(self, config):
        self.practice_tasks = {}
        self.tasks = {}
        self.sensors = {}
        self.config = config

    def _validate_task(self, task: type):
        if not issubclass(task, Task):
            msg = f'{task} must be a subclass of Task'
            raise TypeError(msg)

    def add_task(self, name: str, task: type, order: int, is_practice: bool = False):  # noqa: FBT001, FBT002
        """Register a task (main or practice)."""
        self._validate_task(task)
        remote_class = ray.remote(task)
        task_container = self.practice_tasks if is_practice else self.tasks
        task_container[name] = TaskEntry(order, name, remote_class)

    def register_sensor(self, name: str, sensor_instance: Sensor):
        """Register a sensor instance."""
        if not isinstance(sensor_instance, Sensor):
            msg = f'{sensor_instance} must be an instance of Sensor'
            raise TypeError(msg)
        self.sensors[name] = sensor_instance

    def save_sensor_info(self, sensor_info_save_path='sensor_info.yaml'):
        """Save information of all registered sensors to a YAML file."""
        sensor_info = {
            name: {'config': sensor.config, 'stream_info': sensor.stream_info} for name, sensor in self.sensors.items()
        }

        with Path(sensor_info_save_path).open('w') as f:
            yaml.dump(sensor_info, f, default_flow_style=False)
        sys.stdout(f'Sensor information saved to {sensor_info_save_path}.')

    def collect_sensor_data(self):
        """Collect data from each registered sensor in parallel."""

        @ray.remote
        def read_sensor(sensor):
            return sensor.read()

        sensor_tasks = [read_sensor.remote(sensor_instance) for sensor_instance in self.sensors.values()]
        return ray.get(sensor_tasks)

    def _run_tasks(self, tasks):
        """Run a list of tasks in order."""
        for task in sorted(tasks, key=lambda t: t.order):
            ray.get(task.remote_class.remote().execute.remote())

    def run(self):
        """Run the registered tasks and sensors in parallel."""
        self.verify_sensors()
        self.save_sensor_info()

        if self.config.get('run_practice'):
            self._run_tasks(self.practice_tasks.values())

        self.collect_sensor_data()
        self._run_tasks(self.tasks.values())

    def close(self):
        ray.shutdown()
