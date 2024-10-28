from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from pylsl import StreamInfo, StreamOutlet


@dataclass
class TaskEntry:
    order: int
    name: str
    remote_class: object  # Consider specifying a more precise type if possible


class Trial(ABC):
    def __init__(self, trial_id: str, parameters: dict[str, Any]):
        self.trial_id = trial_id
        self.parameters = parameters
        self.lsl_stream = None
        self.data_to_stream = None

    def create_lsl_stream(self):
        """Create an LSL stream for the trial using the data signature."""
        data_signature = self.get_data_signature()
        num_channels = len(data_signature)

        # Create LSL stream with the data signature
        info = StreamInfo(
            name=data_signature['name'],
            type=data_signature['type'],
            channel_count=num_channels,
            nominal_srate=data_signature['nominal_srate'],
            channel_format=data_signature['channel_format'],
            source_id=data_signature['source_id'],
        )
        self.lsl_stream = StreamOutlet(info)

    @abstractmethod
    def get_data_signature(self) -> list[str]:
        """Return the data signature for this trial."""

    def stream_data(self):
        """Stream data for this trial."""
        if not self.data_to_stream:
            self.lsl_stream.push_sample(self.data_to_stream)

    @abstractmethod
    def execute(self):
        """Execute the trial logic and stream data."""


class Block:
    def __init__(self, block_id: str):
        self.block_id = block_id
        self.trials: list[Trial] = []

    def add_trial(self, trial: Trial, order: int):
        """Add a trial to the block at a specific order and validate data signature."""
        if self.trials:
            existing_signature = self.trials[0].get_data_signature()
            new_signature = trial.get_data_signature()
            if existing_signature != new_signature:
                msg = f'Data signature mismatch: expected {existing_signature}, got {new_signature}'
                raise ValueError(msg)

        # Insert the trial in the specified order
        self.trials.append((order, trial))

        # Sort trials based on the specified order
        self.trials.sort(key=lambda x: x[0])  # Sort by the first element (order)

    def execute(self, order: str):
        """Execute the block of trials."""
        if order == 'random':
            random.shuffle(self.trials)
        else:
            self.trials = [trial for _, trial in self.trials]  # Extract trials only, maintaining sorted order

        for trial in self.trials:
            trial.create_lsl_stream()  # Create LSL stream for the trial
            trial.execute()  # Execute the trial


class Task:
    def __init__(self, name: str):
        self.name = name
        self.blocks: list[Block] = []

    def add_block(self, block: Block):
        """Add a block to the task."""
        self.blocks.append(block)

    def execute(self, order: str = 'predefined'):
        for block in self.blocks:
            block.execute(order)
