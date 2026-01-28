from __future__ import annotations

import logging
import random
from abc import ABC, abstractmethod
from typing import Any

from pylsl import StreamInfo, StreamOutlet

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


class LSLTrial(ABC):
    """
    Base class for LSL streaming trials.

    Subclasses must implement:
    1. ``get_data_signature()`` to define the LSL stream format
    2. ``read_data()`` to return current data to stream
    3. ``execute()`` which must call ``self.stream()`` in the game loop

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
        The LSL stream outlet for pushing data.

    """

    def __init__(self, trial_id: str, parameters: dict[str, Any]):
        self.trial_id = trial_id
        self.parameters = parameters
        self.lsl_stream: StreamOutlet | None = None
        self._has_streamed: bool = False

    def create_lsl_stream(self):
        """
        Create an LSL stream based on the data signature.

        Uses the signature returned by ``get_data_signature()`` to configure
        the LSL StreamInfo and create a StreamOutlet.
        """
        signature = self.get_data_signature()
        info = StreamInfo(
            name=signature['name'],
            type=signature['type'],
            channel_count=signature['channel_count'],
            nominal_srate=signature['nominal_srate'],
            channel_format=signature['channel_format'],
            source_id=signature['source_id'],
        )
        self.lsl_stream = StreamOutlet(info)

    def stream(self):
        """
        Read current data and push to LSL stream.

        Call this method in your game loop during ``execute()``.
        It reads data via ``read_data()`` and pushes it to the LSL outlet.

        Raises
        ------
        RuntimeError
            If ``create_lsl_stream()`` was not called before streaming.

        """
        if self.lsl_stream is None:
            msg = 'LSL stream not created. Call create_lsl_stream() first.'
            raise RuntimeError(msg)

        data = self.read_data()
        if data is not None:
            self.lsl_stream.push_sample(data)
            self._has_streamed = True

    @property
    def has_streamed(self) -> bool:
        """
        Check whether stream() was called with valid data at least once.

        Returns
        -------
        bool
            True if data was streamed at least once, False otherwise.

        """
        return self._has_streamed

    @abstractmethod
    def get_data_signature(self) -> dict[str, Any]:
        """
        Return the LSL stream signature.

        Returns
        -------
        dict[str, Any]
            Dictionary containing LSL stream configuration with keys:

            - name : str
                Stream name.
            - type : str
                Stream type (e.g., 'Markers', 'EEG').
            - channel_count : int
                Number of channels.
            - nominal_srate : float
                Nominal sampling rate in Hz.
            - channel_format : str
                Data format (e.g., 'float32', 'string').
            - source_id : str
                Unique source identifier.

        """

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

        Implementation must:
        1. Call ``self.create_lsl_stream()`` at the start
        2. Call ``self.stream()`` in the game loop to push data

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
    trials : list[tuple[int, Trial | LSLTrial]]
        List of (order, trial) tuples.

    """

    def __init__(self, block_id: str):
        self.block_id = block_id
        self.trials: list[tuple[int, Trial | LSLTrial]] = []

    def add_trial(self, trial: Trial | LSLTrial, order: int):
        """
        Add a trial to the block.

        Parameters
        ----------
        trial : Trial | LSLTrial
            The trial instance to add.
        order : int
            Execution order (lower values execute first).

        """
        self.trials.append((order, trial))
        self.trials.sort(key=lambda x: x[0])

    def execute(self, order: str = 'predefined'):
        """
        Execute all trials in the block.

        Parameters
        ----------
        order : str, optional
            Execution order mode. Options are:

            - 'predefined' : Execute in the order specified by add_trial()
            - 'random' : Randomize trial order

            Default is 'predefined'.

        Raises
        ------
        RuntimeError
            If an LSLTrial did not call ``stream()`` during execution.

        """
        trials_list = [t for _, t in self.trials]

        if order == 'random':
            random.shuffle(trials_list)

        for trial in trials_list:
            trial.execute()

            # Verify streaming for LSLTrial
            if isinstance(trial, LSLTrial) and not trial.has_streamed:
                msg = (
                    f'LSLTrial {trial.trial_id}: stream() was never called during execute(). '
                    'You must call self.stream() in your execution loop.'
                )
                raise RuntimeError(msg)


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
                block.execute(order)
        else:
            msg = 'execute() must be implemented in subclass for tasks without blocks'
            raise NotImplementedError(msg)


# Backwards compatibility aliases
GeneralTask = Task
LSLTask = Task
