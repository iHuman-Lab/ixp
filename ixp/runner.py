# ruff: noqa: G004 EM102
from __future__ import annotations

import logging

import ray

from .sensors.base_sensor import Sensor
from .task import GeneralTask, LSLTask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


# RemoteTask handles tasks in a specific order
@ray.remote
class RemoteTask:
    def __init__(self):
        self.tasks = {}

    def add_task(self, task_name: str, task_cls: type, task_config: dict, order: int):
        task = task_cls(**task_config)
        self.tasks[task_name] = {'task': task, 'order': order}

    def execute(self):
        sorted_tasks = sorted(self.tasks.items(), key=lambda x: x[1]['order'])
        for task_name, task_info in sorted_tasks:
            logger.info(f'Running task {task_name} (Order: {task_info["order"]})')
            task_info['task'].execute()


# RemoteSensor handles sensor recording and streaming
@ray.remote
class RemoteSensor:
    def __init__(self, sensor_name: str, sensor_cls: type, sensor_config: dict):
        self.sensor_name = sensor_name
        self.sensor = sensor_cls(**sensor_config)
        self.sensor.create_lsl_stream()

    def record(self):
        logger.info(f'Recording {self.sensor_name}')
        while self.sensor.recording:
            data = self.sensor.read_data()
            self.sensor.stream_data(data)


# Type validation utility
def validate(instance: object, base_types: tuple[type, ...]):
    if not issubclass(instance, base_types):
        raise TypeError(f'{instance} must be a subclass of {base_types}')


# Main runner for the experiment
class ExperimentRunner:
    def __init__(self, config: dict):
        self.config = config
        self.remote_practice_tasks = RemoteTask.remote()
        self.remote_tasks = RemoteTask.remote()
        self.remote_sensors = {}

    def add_task(
        self,
        name: str,
        task_cls: type,
        task_config: dict,
        order: int,
        is_practice: bool = False,  # noqa: FBT001, FBT002
    ):
        validate(task_cls, (LSLTask, GeneralTask))
        remote_task = self.remote_practice_tasks if is_practice else self.remote_tasks
        remote_task.add_task.remote(name, task_cls, task_config, order)

    def register_sensor(self, name: str, sensor: Sensor):
        """Register a sensor for the experiment."""
        validate(sensor, Sensor)
        self.remote_sensors[name] = RemoteSensor.remote(name, sensor)

    def run(self):
        """Run tasks and sensors in parallel."""
        tasks_and_sensors = [sensor.record.remote() for sensor in self.remote_sensors.values()]
        if self.config.get('run_practice', False):
            tasks_and_sensors.append(self.remote_practice_tasks.execute.remote())
        tasks_and_sensors.append(self.remote_tasks.execute.remote())
        ray.get(tasks_and_sensors)

    def close(self):
        """Shut down Ray."""
        ray.shutdown()
