from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import ray
import yaml

from .sensors.base_sensor import Sensor
from .task import Task


@dataclass
class TaskEntry:
    """Holds metadata for a task."""

    order: int
    task_config: dict
    name: str
    remote_class: object  # The Ray remote class


@dataclass
class SensorEntry:
    """Holds metadata for a sensor."""

    name: str
    sensor_config: dict
    remote_class: object  # The Ray remote class for the sensor


def validate(instance: type, base_type: type):
    if not issubclass(instance, base_type):
        msg = f'{instance} must be a subclass of {base_type}'
        raise TypeError(msg)


class ExperimentRunner:
    def __init__(self, config):
        self.practice_tasks = {}
        self.tasks = {}
        self.sensors = {}
        self.config = config

    def add_task(self, name: str, task: type, task_config: dict, order: int, is_practice: bool = False):  # noqa: FBT001, FBT002, PLR0913
        """Register a task (main or practice)."""
        validate(task, Task)
        remote_class = ray.remote(task)
        actor_handle = remote_class.remote(task_config)
        if is_practice:
            self.practice_tasks[name] = TaskEntry(order, name, task_config, actor_handle)
        else:
            self.tasks[name] = TaskEntry(order, name, task_config, actor_handle)

    def register_sensor(self, name: str, sensor: type, sensor_config: dict):
        """Register a sensor instance."""
        validate(sensor, Sensor)
        remote_class = ray.remote(sensor)
        actor_handle = remote_class.remote(sensor_config)
        self.sensors[name] = SensorEntry(name, sensor_config, actor_handle)

    def save_sensor_info(self, sensor_info_save_path='sensor_info.yaml'):
        """Save information of all registered sensors to a YAML file."""
        sensor_info = {
            name: {
                'config': sensor.sensor_config,
                'stream_data_signature': ray.get(sensor.remote_class.get_data_signature.remote()),
            }
            for name, sensor in self.sensors.items()
        }

        with Path(sensor_info_save_path).open('w') as f:
            yaml.dump(sensor_info, f, default_flow_style=False)

        msg = f'Sensor information saved to {sensor_info_save_path}.'
        logging.info(msg)

    def collect_sensor_data(self):
        """Collect data from each registered sensor in parallel."""
        # Collect data by executing 'execute' on each Ray actor (sensor)
        sensor_tasks = [sensor.remote_class.read_data.remote() for sensor in self.sensors.values()]
        return ray.get(sensor_tasks)

    def _run_tasks(self, tasks):
        """Run a list of tasks in order."""
        for task in sorted(tasks, key=lambda t: t.order):
            ray.get(task.remote_class.execute.remote())

    def run(self):
        """Run the registered tasks and sensors in parallel."""
        self.save_sensor_info()

        if self.config.get('run_practice'):
            self._run_tasks(self.practice_tasks.values())

        self.collect_sensor_data()
        self._run_tasks(self.tasks.values())

    def close(self):
        ray.shutdown()
