# vs_task.py
from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from psychopy import core, event, visual

from ixp.task import Block, Task, Trial

# Constants for PsychoPy orientation (PsychoPy 0 is Up, 90 is Right)
# We map your 0, 90, 180, 270 logic accordingly
ANGLE_MAP = {0: 'up', 90: 'left', 180: 'down', 270: 'right'}
KEY_MAP = {'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right'}

MODULE_DIR = Path(__file__).parent


class VSTrial(Trial):
    def __init__(self, trial_id: str, parameters: dict[str, Any]):
        super().__init__(trial_id, parameters)
        self.cfg = parameters
        self.stims = []

    def initialize(self):
        self.win = self.cfg['_window']
        self.rows = self.cfg['rows']
        self.cols = self.cfg['cols']
        self.angles = self.cfg['angles']

        # Stimulus scaling
        screen_h = 1.0  # height units
        scale_factor = self.cfg.get('stimulus_scale', 0.10)
        size = scale_factor

        # Determine Grid Layout
        # Grid spans from -0.4 to 0.4 in height units to leave margins
        grid_height = 0.8
        grid_width = grid_height * (self.win.size[0] / self.win.size[1])

        x_start = -(grid_width * 0.4)
        y_start = 0.4
        x_step = (grid_width * 0.8) / max(1, self.cols - 1) if self.cols > 1 else 0
        y_step = 0.8 / max(1, self.rows - 1) if self.rows > 1 else 0

        target_index = random.randint(0, self.rows * self.cols - 1)
        self.target_angle = random.choice(self.angles)
        self.correct_answer = ANGLE_MAP[self.target_angle]

        self.stims = []
        for index in range(self.rows * self.cols):
            row, col = divmod(index, self.cols)
            pos = (x_start + col * x_step, y_start - row * y_step)

            if index == target_index:
                image_path = MODULE_DIR / 'T.png'
                angle = self.target_angle
            else:
                image_path = MODULE_DIR / f'{random.choice(["L1", "L2"])}.png'
                angle = random.choice(self.angles)

            stim = visual.ImageStim(
                self.win,
                image=str(image_path),
                pos=pos,
                size=(size, size),
                ori=angle,  # PsychoPy uses degrees
                units='height',
            )
            self.stims.append(stim)

    def execute(self):
        # 1. Fixation
        # (Assuming your show_fixation utility is updated for PsychoPy)
        fixation = visual.TextStim(self.win, text='+', color='black', height=0.05)
        fixation.draw()
        self.win.flip()
        core.wait(self.cfg.get('fixation_time', 2000) / 1000.0)

        # 2. Show Stimuli
        for s in self.stims:
            s.draw()
        self.win.flip()

        # 3. Wait for Response
        start_time = core.getTime()
        timeout = self.cfg.get('response_timeout', 5)

        # Clear previous keys
        event.clearEvents()

        response = 'timeout'
        rt = timeout

        while core.getTime() - start_time < timeout:
            keys = event.getKeys(keyList=['up', 'down', 'left', 'right', 'escape'])
            if 'escape' in keys:
                core.quit()
            if keys:
                response = keys[0]
                rt = core.getTime() - start_time
                break

            # Keep drawing stimuli during wait to prevent flickering
            for s in self.stims:
                s.draw()
            self.win.flip()

        return response, self.correct_answer, rt

    def clean_up(self):
        self.stims = []


class VS(Task):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        block = Block('vs_block')

        for trial_idx in range(config['total_trials']):
            trial = VSTrial(trial_id=f'trial_{trial_idx}', parameters=config)
            block.add_trial(trial, order=trial_idx)

        self.add_block(block)

    def execute(self, order: str = 'predefined'):
        self.config['_window'] = visual.Window(
            size=self.config.get('window_size', [1100, 800]),
            units='height',
            color=[0.5, 0.5, 0.5],  # RGB -1 to 1 or normalized
            fullscr=self.config.get('fullscreen', False),
        )
        try:
            for block in self.blocks:
                block.execute(order)
        finally:
            self.config['_window'].close()
