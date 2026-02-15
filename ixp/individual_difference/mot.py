from __future__ import annotations

import math
import random
from typing import Any

from psychopy import core, event, visual

# Assuming these are available in your framework
from ixp.task import Block, Task, Trial


class MOTTrial(Trial):
    """
    Multiple Object Tracking trial using PsychoPy.
    """

    def __init__(self, trial_id: str, parameters: dict[str, Any]):
        super().__init__(trial_id, parameters)
        self.cfg = parameters
        self.circles = []

    def initialize(self):
        """
        Prepare stimuli before the trial starts.
        Requires self.cfg['_window'] to be set by the Task.
        """
        self.win = self.cfg['_window']
        self.num_objects = self.cfg.get('num_objects', 8)
        self.num_targets = self.cfg.get('num_targets', 3)
        self.radius = self.cfg.get('radius_scale', 0.025)
        self.speed = self.cfg.get('speed_scale', 0.005)

        self.target_indices = random.sample(range(self.num_objects), self.num_targets)

        # Calculate bounds based on current window aspect ratio
        aspect_ratio = self.win.size[0] / self.win.size[1]
        x_lim = (0.5 * aspect_ratio) - self.radius
        y_lim = 0.5 - self.radius

        self.circles = []
        for i in range(self.num_objects):
            is_target = i in self.target_indices
            pos = [random.uniform(-x_lim, x_lim), random.uniform(-y_lim, y_lim)]

            stim = visual.Circle(
                self.win,
                radius=self.radius,
                pos=pos,
                fillColor='black' if is_target else 'white',
                lineColor=None,
                units='height',
            )

            angle = random.uniform(0, 2 * math.pi)
            vel = [self.speed * math.cos(angle), self.speed * math.sin(angle)]

            self.circles.append({'stim': stim, 'vel': vel, 'is_target': is_target})

    def _update_motion(self):
        """Internal helper for frame-by-frame updates."""
        aspect_ratio = self.win.size[0] / self.win.size[1]
        x_lim = (0.5 * aspect_ratio) - self.radius
        y_lim = 0.5 - self.radius

        for c in self.circles:
            pos = c['stim'].pos
            vel = c['vel']

            new_x, new_y = pos[0] + vel[0], pos[1] + vel[1]

            if abs(new_x) >= x_lim:
                vel[0] *= -1
                new_x = math.copysign(x_lim, new_x)
            if abs(new_y) >= y_lim:
                vel[1] *= -1
                new_y = math.copysign(y_lim, new_y)

            c['stim'].pos = (new_x, new_y)

    def _target_phase(self):
        display_timer = core.CountdownTimer(self.cfg.get('target_display_time', 1.5))
        while display_timer.getTime() > 0:
            for c in self.circles:
                c['stim'].draw()
            self.win.flip()

    def _tracking_phase(self):
        for c in self.circles:
            c['stim'].fillColor = 'white'

        tracking_timer = core.CountdownTimer(self.cfg.get('trial_time', 5))
        while tracking_timer.getTime() > 0:
            self._update_motion()
            for c in self.circles:
                c['stim'].draw()
            self.win.flip()
            if 'escape' in event.getKeys():
                core.quit()

    def _selection_phase(self):
        mouse = event.Mouse(win=self.win)
        selected = []
        event.clearEvents()
        while len(selected) < self.num_targets:
            for c in self.circles:
                c['stim'].draw()
            self.win.flip()

            if mouse.getPressed()[0]:
                m_pos = mouse.getPos()
                for c in self.circles:
                    if c['stim'].contains(m_pos) and c not in selected:
                        c['stim'].fillColor = 'red'
                        selected.append(c)

                        for stim_to_draw in self.circles:
                            stim_to_draw['stim'].draw()
                        self.win.flip()

                        while mouse.getPressed()[0]:
                            pass  # Debounce

        core.wait(2.0)
        return selected

    def execute(self) -> int:
        """Main trial logic loop."""
        # 1. Target Phase (Show targets)
        self._target_phase()

        # 2. Tracking Phase (All white, moving)
        self._tracking_phase()

        # 3. Selection Phase
        selected = self._selection_phase()
        return sum(1 for c in selected if c['is_target'])

    def clean_up(self):
        """Clear references to stimuli to free memory."""
        self.circles = []


class MOT(Task):
    """
    Multiple Object Tracking task containing a block of MOTTrials.
    """

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        # Create the block logic (assuming your framework uses Block/Trial architecture)
        self.block = Block('mot_block')
        for trial_idx in range(config.get('total_trials', 5)):
            trial = MOTTrial(trial_id=f'trial_{trial_idx}', parameters=config)
            self.block.add_trial(trial, order=trial_idx)
        self.add_block(self.block)

    def execute(self, order: str = 'predefined'):
        # Initialize the PsychoPy window
        self.config['_window'] = visual.Window(
            size=self.config.get('window_size', [1000, 800]),
            units='height',
            color=[0.5, 0.5, 0.5],  # Neutral grey
            fullscr=self.config.get('fullscreen', False),
        )

        try:
            results = []
            for block in self.blocks:
                block_results = block.execute(order)
                results.append(block_results)
            return results
        finally:
            self.config['_window'].close()
