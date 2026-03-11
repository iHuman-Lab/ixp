# ruff: noqa: G004
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, NamedTuple

import ray
from psychopy import visual

from .instruction import InstructionScreen
from .task import Task
from .utils import save_task_results

if TYPE_CHECKING:
    from .sensors.base_sensor import Sensor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskEntry(NamedTuple):
    order: int
    name: str
    task_cls: type
    task_config: dict[str, Any]
    pages: list[str]


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
        self.tasks: list[TaskEntry] = []
        self.practice_tasks: list[TaskEntry] = []
        self.sensors: dict[str, ray.actor.ActorHandle] = {}
        self.actors: dict[str, ray.actor.ActorHandle] = {}

    def add_task(  # noqa: PLR0913
        self,
        name: str,
        task_cls: type,
        task_config: dict[str, Any],
        order: int = 0,
        is_practice: bool = False,  # noqa: FBT001, FBT002
        instructions: list[str] | str | None = None,
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
        instructions : list[str] | str | None, optional
            Instruction text to display before this task runs. A single string
            or a list of strings (shown as separate pages). Default is None.

        Raises
        ------
        TypeError
            If task_cls does not inherit from Task.

        """
        if not issubclass(task_cls, Task):
            msg = 'task_cls must inherit from Task'
            raise TypeError(msg)

        pages = [instructions] if isinstance(instructions, str) else (instructions or [])

        entry = TaskEntry(
            order=order,
            name=name,
            task_cls=task_cls,
            task_config=task_config,
            pages=pages,
        )
        if is_practice:
            self.practice_tasks.append(entry)
        else:
            self.tasks.append(entry)

        actor = ray.remote(task_cls).remote(**task_config)
        ray.get(actor.is_ready.remote())
        ray.get(actor.create_lsl_stream.remote())  # no-op if get_data_signature() returns None
        self.actors[name] = actor

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

    def _run_task(
        self,
        task_name: str,
        task_actor: ray.actor.ActorHandle,
        instructions: list[str] | None = None,
    ) -> None:
        """
        Run a single task and synchronize sensors.

        Parameters
        ----------
        task_name : str
            Name of the task to run.
        task_actor : ray.actor.ActorHandle
            Ray actor handle for the task.
        instructions : list[str] | None, optional
            Pages of instruction text to display before the task runs.

        """
        logger.info(f'Running task: {task_name}')

        # Show instructions before the task if provided
        if instructions:
            win = visual.Window(fullscr=False, color='black', units='height', checkTiming=False)
            InstructionScreen(win).show_pages(instructions)
            win.close()

        ray.get(task_actor.initial_setup.remote())

        # Notify sensors of task context
        for sensor in self.sensors.values():
            sensor.set_task.remote(task_name)

        # Execute task (blocking) and collect results
        results = ray.get(task_actor.execute.remote())

        # Save to CSV if the task returned row data (non-streaming tasks)
        if results and isinstance(results, list) and isinstance(results[0], dict):
            save_task_results(task_name, results, {})

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

        practice_tasks = sorted(self.practice_tasks)
        main_tasks = sorted(self.tasks)

        run_practice = self.config.get('run_practice', False)

        for sensor in self.sensors.values():
            sensor.start.remote()

        try:
            if run_practice:
                for entry in practice_tasks:
                    self._run_task(entry.name, self.actors[entry.name], entry.pages)

            for entry in main_tasks:
                self._run_task(entry.name, self.actors[entry.name], entry.pages)
        finally:
            for sensor in self.sensors.values():
                sensor.stop.remote()

        logger.info('Experiment finished')

    def close(self) -> None:
        """
        Shut down Ray.

        """
        ray.shutdown()
