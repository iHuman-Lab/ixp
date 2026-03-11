from __future__ import annotations

import logging
import random
from abc import ABC, abstractmethod
from typing import Any

from pylsl import StreamInfo, StreamOutlet

from .utils import StreamGuard

logger = logging.getLogger(__name__)


class Trial(ABC):
    """
    Base class for non-streaming trials.

    Parameters
    ----------
    trial_id : str
        Unique identifier for the trial.
    parameters : dict[str, Any]
        Configuration parameters for the trial.

    Attributes
    ----------
    trial_id : str
        Unique identifier for the trial.
    parameters : dict[str, Any]
        Configuration parameters for the trial.

    """

    def __init__(self, trial_id: str, parameters: dict[str, Any]):
        self.trial_id = trial_id
        self.parameters = parameters

    @abstractmethod
    def initialize(self) -> Any:
        """
        Initialize the trial
        """

    @abstractmethod
    def execute(self) -> Any:
        """
        Run the trial logic.

        This method should implement stimuli presentation, response collection,
        and any other trial-specific logic.

        Returns
        -------
        Any
            Trial result data (e.g., response, reaction time, score).

        """

    @abstractmethod
    def clean_up(self) -> Any:
        """
        Clean up after the trial
        """


class LSLTrial(Trial):
    """
    Base class for LSL streaming trials.

    The parent task owns the LSL stream outlet. Subclasses must implement:
    1. ``read_data()`` to return current data to stream
    2. ``execute()`` which must call ``self.stream()`` in the game loop

    The ``lsl_stream`` outlet is injected by ``Block.execute()`` before the
    trial runs; subclasses do not create it themselves.

    Parameters
    ----------
    trial_id : str
        Unique identifier for the trial.
    parameters : dict[str, Any]
        Configuration parameters for the trial.

    Attributes
    ----------
    trial_id : str
        Unique identifier for the trial.
    parameters : dict[str, Any]
        Configuration parameters for the trial.
    lsl_stream : StreamOutlet | None
        The LSL stream outlet injected by the task before execution.

    """

    def __init__(self, trial_id: str, parameters: dict[str, Any]):
        super().__init__(trial_id, parameters)
        self.lsl_stream: StreamOutlet | None = None
        self._stream_called: bool = False
        self._samples_pushed: int = 0

    def stream(self):
        """
        Read current data and push to the task's LSL stream.

        Call this method in your game loop during ``execute()``.
        It reads data via ``read_data()`` and pushes it to the LSL outlet.

        Raises
        ------
        RuntimeError
            If the task has no LSL stream outlet.

        """
        if self.lsl_stream is None:
            msg = f'LSLTrial "{self.trial_id}": no LSL stream outlet. Ensure the task defines get_data_signature().'
            raise RuntimeError(msg)

        self._stream_called = True

        data = self.read_data()
        if data is not None:
            self.lsl_stream.push_sample(data)
            self._samples_pushed += 1

    @property
    def stream_was_called(self) -> bool:
        """True if stream() was called at least once."""
        return self._stream_called

    @property
    def has_streamed(self) -> bool:
        """True if at least one sample was pushed to LSL."""
        return self._samples_pushed > 0

    @abstractmethod
    def read_data(self) -> list[Any] | None:
        """
        Return current data to stream.

        Called by ``stream()`` method to get the current trial state.

        Returns
        -------
        list[Any] | None
            Data sample to stream, or None to skip this cycle.

        """

    @abstractmethod
    def execute(self) -> Any:
        """
        Run the trial logic with LSL streaming.

        Implementation must call ``self.stream()`` in the game loop to push data.
        The ``lsl_stream`` outlet is set by the task before this is called.

        Returns
        -------
        Any
            Trial result data.

        Raises
        ------
        RuntimeError
            Raised by Block if ``stream()`` was never called during execution.

        """


class Block:
    """
    A block containing multiple trials with execution order control.

    Supports both Trial and LSLTrial types. For LSLTrial instances,
    verifies that streaming occurred during execution.

    Parameters
    ----------
    block_id : str
        Unique identifier for the block.

    Attributes
    ----------
    block_id : str
        Unique identifier for the block.
    trials : list[tuple[int, Trial]]
        List of (order, trial) tuples.

    """

    def __init__(self, block_id: str):
        self.block_id = block_id
        self.trials: list[tuple[int, Trial]] = []

    def add_trial(self, trial: Trial, order: int):
        """
        Add a trial to the block.

        Parameters
        ----------
        trial : Trial
            The trial instance to add.
        order : int
            Execution order (lower values execute first).

        """
        self.trials.append((order, trial))
        self.trials.sort(key=lambda x: x[0])

    def execute(self, order: str = 'predefined', lsl_stream: StreamOutlet | None = None):
        """
        Execute all trials in the block.

        Parameters
        ----------
        order : str, optional
            Execution order mode. Options are:

            - 'predefined' : Execute in the order specified by add_trial()
            - 'random' : Randomize trial order

            Default is 'predefined'.
        lsl_stream : StreamOutlet | None, optional
            The task-level LSL outlet to inject into each LSLTrial.

        Raises
        ------
        RuntimeError
            If an LSLTrial did not call ``stream()`` during execution.

        """
        trials_list = [t for _, t in self.trials]

        if order == 'random':
            random.shuffle(trials_list)

        results = []
        for trial in trials_list:
            trial.initialize()
            if isinstance(trial, LSLTrial):
                trial.lsl_stream = lsl_stream
                with StreamGuard(trial):
                    trial.execute()
            else:
                result = trial.execute()
                if result is not None:
                    results.append(result)
            trial.clean_up()
        return results


class Task(ABC):
    """
    Base class for tasks containing blocks and trials.

    Parameters
    ----------
    config : dict[str, Any]
        Configuration dictionary for the task.

    Attributes
    ----------
    config : dict[str, Any]
        Configuration dictionary for the task.
    blocks : list[Block]
        List of blocks in the task.

    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.blocks: list[Block] = []
        self.lsl_stream: StreamOutlet | None = None

    def is_ready(self) -> bool:
        """Return True once the actor is initialised (used as a Ray sync barrier)."""
        return True

    def get_data_signature(self) -> dict[str, Any] | None:
        """
        Return the LSL stream signature for this task, or None for no stream.

        Override in subclass to define a task-level LSL stream. Returns a dict
        with keys: name, type, channel_count, nominal_srate, channel_format, source_id.
        """
        return None

    def create_lsl_stream(self):
        """
        Create the task-level LSL stream from ``get_data_signature()``.

        Called automatically by ``Experiment.add_task()``. Does nothing if
        ``get_data_signature()`` returns None.
        """
        signature = self.get_data_signature()
        if signature is None:
            return
        info = StreamInfo(
            name=signature['name'],
            type=signature['type'],
            channel_count=signature['channel_count'],
            nominal_srate=signature['nominal_srate'],
            channel_format=signature['channel_format'],
            source_id=signature['source_id'],
        )
        self.lsl_stream = StreamOutlet(info)

    def initial_setup(self):  # noqa: B027
        """
        Perform initial setup before task execution.

        Override in subclass to initialize windows, load images,
        or set up other resources. Called before blocks are executed.
        """

    def add_block(self, block: Block):
        """
        Add a block to the task.

        Parameters
        ----------
        block : Block
            The block to add.

        """
        self.blocks.append(block)

    @abstractmethod
    def execute(self, order: str = 'predefined'):
        """
        Execute the task.

        Default implementation runs all blocks sequentially.
        Override for custom behavior.

        Parameters
        ----------
        order : str, optional
            Execution order mode passed to each block.
            Default is 'predefined'.

        Raises
        ------
        NotImplementedError
            If no blocks exist and subclass doesn't override this method.

        """
        if self.blocks:
            for block in self.blocks:
                block.execute(order, lsl_stream=self.lsl_stream)
        else:
            msg = 'execute() must be implemented in subclass for tasks without blocks'
            raise NotImplementedError(msg)
