# ruff: noqa: G004
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import ray

from .task import Task

if TYPE_CHECKING:
    from .sensors.base_sensor import Sensor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    Parameters
    ----------
    name : str
        Unique identifier for the sensor.
    sensor_cls : type[Sensor]
        The sensor class to instantiate.
    sensor_config : dict[str, Any]
        Configuration dictionary passed to the sensor constructor.
    sample_interval : float, optional
        Optional throttling interval in seconds between samples.

    Attributes
    ----------
    name : str
        Unique identifier for the sensor.
    sensor : Sensor
        The instantiated sensor instance.
    recording : bool
        Whether the sensor is currently recording.
    current_task : str
        Name of the current task context.
    sample_interval : float or None
        Throttling interval between samples.

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
        self.sensor.initialize()
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
                if sample is not None:
                    self.sensor.stream_data(sample)
                if self.sample_interval is not None:
                    time.sleep(self.sample_interval)
            except Exception as exc:  # noqa: PERF203
                logger.exception(f'[Sensor] Error in {self.name}: {exc}')  # noqa: TRY401
                time.sleep(0.01)

        logger.info(f'[Sensor] Stopped {self.name}')

    def stop(self) -> None:
        """
        Stop sensor recording.

        """
        self.recording = False

    def set_task(self, task_name: str) -> None:
        """
        Set the current task context for this sensor.

        Parameters
        ----------
        task_name : str
            Name of the current task.

        """
        self.current_task = task_name


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

    Parameters
    ----------
    config : dict[str, Any]
        Experiment-level configuration dictionary.

    Attributes
    ----------
    config : dict[str, Any]
        Experiment-level configuration dictionary.
    tasks : list[tuple[str, ray.actor.ActorHandle]]
        List of registered main tasks.
    practice_tasks : list[tuple[str, ray.actor.ActorHandle]]
        List of registered practice tasks.
    sensors : dict[str, ray.actor.ActorHandle]
        Dictionary of registered sensors.

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
        order: int = 0,
        is_practice: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """
        Register a task with the experiment.

        Parameters
        ----------
        name : str
            Unique name for the task.
        task_cls : type
            The task class to instantiate (must inherit from Task).
        task_config : dict[str, Any]
            Configuration dictionary passed to the task constructor.
        order : int, optional
            Execution order (lower values execute first). Default is 0.
        is_practice : bool, optional
            If True, registers as a practice task. Default is False.

        Raises
        ------
        TypeError
            If task_cls does not inherit from Task.

        """
        if not issubclass(task_cls, Task):
            msg = 'task_cls must inherit from Task'
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
        sample_interval: float | None = None,
    ) -> None:
        """
        Register a sensor for the experiment.

        Parameters
        ----------
        name : str
            Unique name for the sensor.
        sensor_cls : type
            The sensor class to instantiate (must inherit from Sensor).
        sensor_config : dict[str, Any]
            Configuration dictionary passed to the sensor constructor.
        sample_interval : float, optional
            Optional throttling interval in seconds between samples.

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

        Raises
        ------
        ValueError
            If no tasks are registered

        """
        if not self.tasks and not self.practice_tasks:
            msg = 'No tasks registered. Use add_task() before running.'
            raise ValueError(msg)

        logger.info('Starting experiment')

        # Sort tasks by order
        practice_tasks = sorted(self.practice_tasks, key=lambda x: x[2])
        main_tasks = sorted(self.tasks, key=lambda x: x[2])

        # 1. Start sensors (parallel, non-blocking)
        for sensor in self.sensors.values():
            sensor.start.remote()

        try:
            # 2. Run practice tasks
            if self.config.get('run_practice', False):
                for task_name, task_actor, _ in practice_tasks:
                    self._run_task(task_name, task_actor)

            # 3. Run main tasks
            for task_name, task_actor, _ in main_tasks:
                self._run_task(task_name, task_actor)
        finally:
            # 4. Stop sensors (always executed, even on task failure)
            for sensor in self.sensors.values():
                sensor.stop.remote()

        logger.info('Experiment finished')

    def _run_task(self, task_name: str, task_actor: ray.actor.ActorHandle) -> None:
        """
        Run a single task and synchronize sensors.

        Parameters
        ----------
        task_name : str
            Name of the task to run.
        task_actor : ray.actor.ActorHandle
            Ray actor handle for the task.

        """
        logger.info(f'Running task: {task_name}')

        # Notify sensors of task context
        for sensor in self.sensors.values():
            sensor.set_task.remote(task_name)

        # Execute task (blocking)
        ray.get(task_actor.execute.remote())

    def close(self) -> None:
        """
        Shut down Ray.

        """
        ray.shutdown()
