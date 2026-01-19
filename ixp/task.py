from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Any

from pylsl import StreamInfo, StreamOutlet


class Trial(ABC):
    """
    Base class for a trial.

    Each trial may optionally stream LSL data, or simply save data locally.
    """

    def __init__(self, trial_id: str, parameters: dict[str, Any]):
        self.trial_id = trial_id
        self.parameters = parameters
        self.lsl_stream: StreamOutlet | None = None
        self.data_to_stream: list[Any] | None = None

    def create_lsl_stream(self):
        """
        Create an LSL stream for the trial.
        Only needed if the trial streams via LSL.
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

    def stream_data(self):
        """Push the data_to_stream to the LSL outlet (if created)."""
        if self.lsl_stream is None:
            msg = 'LSL stream not created yet'
            raise RuntimeError(msg)
        if self.data_to_stream is None:
            msg = 'No data to stream'
            raise RuntimeError(msg)
        self.lsl_stream.push_sample(self.data_to_stream)

    @abstractmethod
    def get_data_signature(self) -> dict[str, Any]:
        """Return the trial’s LSL data signature. Required for LSL trials; optional for save-only trials."""

    @abstractmethod
    def execute(self) -> None:
        """Run the trial logic (stimuli, response collection, streaming/saving)."""


class Block:
    """
    A block contains multiple trials and handles execution order.
    """

    def __init__(self, block_id: str):
        self.block_id = block_id
        self.trials: list[tuple[int, Trial]] = []  # list of (order, trial)

    def add_trial(self, trial: Trial, order: int):
        """Add a trial to the block in a specific order."""
        if self.trials:
            # Optional: ensure all LSL trials have the same signature
            existing_signature = self.trials[0][1].get_data_signature()
            new_signature = trial.get_data_signature()
            if existing_signature != new_signature and existing_signature['type'] != 'none':
                msg = f'Data signature mismatch: expected {existing_signature}, got {new_signature}'
                raise ValueError(msg)

        self.trials.append((order, trial))
        self.trials.sort(key=lambda x: x[0])

    def execute(self, order: str = 'predefined'):
        """Execute all trials in the block, respecting the specified order."""
        trials_list = [t for _, t in self.trials]

        if order == 'random':
            random.shuffle(trials_list)

        for trial in trials_list:
            # Only create LSL stream if trial uses it
            if trial.get_data_signature()['type'] != 'none':
                trial.create_lsl_stream()
            trial.execute()


class GeneralTask(ABC):
    """
    Base class for any task, with optional blocks/trials.
    Trials may or may not use LSL.
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.blocks: list[Block] = []

    def initial_setup(self):  # noqa: B027
        """
        Optional: Override in subclass.
        Use this for initializing windows, loading images, or other resources.
        """

    def add_block(self, block: Block):
        self.blocks.append(block)

    @abstractmethod
    def execute(self, order: str = 'predefined'):
        """
        Execute the task:
        - If blocks exist, run each block
        - Otherwise, implement single-trial or task-level logic in subclass
        """
        if self.blocks:
            for block in self.blocks:
                block.execute(order)
        else:
            msg = 'execute() must be implemented in subclass for tasks without blocks'
            raise NotImplementedError(msg)


class LSLTask(GeneralTask):
    """
    Task designed for LSL streaming experiments.
    Trials handle their own LSL streams.
    Inherits block/trial handling from GeneralTask.
    """

    def execute(self, order: str = 'predefined'):
        """Run all blocks; LSL handled at trial level."""
        if self.blocks:
            for block in self.blocks:
                block.execute(order)
        else:
            msg = 'LSLTask requires blocks/trials; override execute() if needed'
            raise NotImplementedError(msg)
