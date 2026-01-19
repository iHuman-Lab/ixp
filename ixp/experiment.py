# ruff: noqa: G004
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import ray
from pylsl import local_clock

from .task import GeneralTask, LSLTask

if TYPE_CHECKING:
    from .sensors.base_sensor import Sensor

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
    """
    Ray actor that controls the lifecycle of a Sensor.

    Responsibilities:
    - Start / stop sensor recording
    - Run the continuous read → stream loop
    - Annotate data with task context (via markers)
    - Remain independent of task logic
    """

    def __init__(
        self,
        name: str,
        sensor_cls: type[Sensor],
        sensor_config: dict[str, Any],
        sample_interval: float | None = None,
    ):
        self.name = name
        self.sensor = sensor_cls(sensor_config)
        self.sensor.create_lsl_stream()

        self.recording: bool = False
        self.current_task: str = 'INIT'
        self.sample_interval = sample_interval  # Optional throttling

    def start(self) -> None:
        """
        Start continuous sensor recording.
        This method is non-blocking when called via Ray.
        """
        logger.info(f'[Sensor] Starting {self.name}')
        self.recording = True

        while self.recording:
            try:
                sample = self.sensor.read_data()
                self.sensor.stream_data(sample)
                if self.sample_interval is not None:
                    time.sleep(self._sample_interval)
            except Exception as exc:  # noqa: PERF203
                logger.exception(f'[Sensor] Error in {self.name}: {exc}')  # noqa: TRY401
                time.sleep(0.01)

        logger.info(f'[Sensor] Stopped {self.name}')

    def stop(self) -> None:
        """Stop sensor recording."""
        self._recording = False

    def push_marker(self, marker: str) -> None:
        """
        Push an event marker to LSL.

        Use for:
        - TASK_START / TASK_END
        - BLOCK_START / BLOCK_END
        - TRIAL_START / TRIAL_END
        """
        timestamp = local_clock()
        logger.info(f'[Marker] {marker} @ {timestamp}')


# Main runner for the experiment
class Experiment:
    """
    Top-level experiment orchestrator.

    Responsibilities:
    - Register sensors and tasks
    - Start sensors in parallel
    - Run tasks sequentially
    - Stop sensors cleanly
    - Own experiment-level configuration
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.tasks: list[tuple[str, ray.actor.ActorHandle]] = []
        self.practice_tasks: list[tuple[str, ray.actor.ActorHandle]] = []
        self.sensors: dict[str, ray.actor.ActorHandle] = {}

    def add_task(
        self,
        name: str,
        task_cls: type,
        task_config: dict[str, Any],
        *,
        order: int = 0,
        is_practice: bool = False,
    ) -> None:
        """
        Register a task with the experiment.
        """
        if not issubclass(task_cls, (GeneralTask, LSLTask)):
            msg = 'task_cls must inherit from GeneralTask or LSLTask'
            raise TypeError(msg)

        task_actor = ray.remote(task_cls).remote(**task_config)

        if is_practice:
            self.practice_tasks.append((name, task_actor, order))
        else:
            self.tasks.append((name, task_actor, order))

    def register_sensor(
        self,
        name: str,
        sensor_cls: type,
        sensor_config: dict[str, Any],
        *,
        sample_interval: float | None = None,
    ) -> None:
        """
        Register a sensor for the experiment.
        """
        self.sensors[name] = RemoteSensor.remote(
            name=name,
            sensor_cls=sensor_cls,
            sensor_config=sensor_config,
            sample_interval=sample_interval,
        )

    def run(self) -> None:
        """
        Run the full experiment.
        """
        logger.info('Starting experiment')

        # Sort tasks by order
        practice_tasks = sorted(self.practice_tasks, key=lambda x: x[2])
        main_tasks = sorted(self.tasks, key=lambda x: x[2])

        # 1. Start sensors (parallel, non-blocking)
        for sensor in self.sensors.values():
            sensor.start.remote()

        # 2. Run practice tasks
        if self.config.get('run_practice', False):
            for task_name, task_actor, _ in practice_tasks:
                self._run_task(task_name, task_actor)

        # 3. Run main tasks
        for task_name, task_actor, _ in main_tasks:
            self._run_task(task_name, task_actor)

        # 4. Stop sensors
        for sensor in self.sensors.values():
            sensor.stop.remote()

        logger.info('Experiment finished')

    def _run_task(self, task_name: str, task_actor: ray.actor.ActorHandle) -> None:
        """
        Run a single task and synchronize sensors.
        """
        logger.info(f'Running task: {task_name}')

        # Notify sensors of task start
        for sensor in self.sensors.values():
            sensor.set_task.remote(task_name)
            sensor.push_marker.remote(f'TASK_START:{task_name}')

        # Execute task (blocking)
        ray.get(task_actor.execute.remote())

        # Notify sensors of task end
        for sensor in self.sensors.values():
            sensor.push_marker.remote(f'TASK_END:{task_name}')

    def close(self) -> None:
        """
        Shut down Ray.
        """
        ray.shutdown()
