# vs_task.py
from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Any

import pygame

from ixp.individual_difference.utils import (
    check_quit,
    create_window,
    parse_color,
    show_fixation,
)
from ixp.task import Block, GeneralTask, Trial

MODULE_DIR = Path(__file__).parent

ARROW_KEYS = {pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT}
KEY_TO_NAME = {pygame.K_UP: 'up', pygame.K_DOWN: 'down', pygame.K_LEFT: 'left', pygame.K_RIGHT: 'right'}
ANGLE_TO_NAME = {0: 'up', 90: 'left', 180: 'down', 270: 'right'}


class VSTrial(Trial):
    def __init__(self, trial_id: str, parameters: dict[str, Any], window: pygame.Surface):
        super().__init__(trial_id, parameters)
        self.cfg = parameters
        self.window = window
        self.font = pygame.font.Font(None, 80)
        self.images = self._load_images()
        self.background_color = parse_color(self.cfg, 'background_color', [120, 120, 120])
        self.fixation_color = parse_color(self.cfg, 'fixation_color', [0, 0, 0])

    def _load_images(self) -> dict[str, pygame.Surface]:
        size = self.cfg.get('stimulus_size', 60)
        images = {}
        for name in ['T', 'L1', 'L2']:
            path = MODULE_DIR / f'{name}.png'
            img = pygame.image.load(str(path)).convert_alpha()
            images[name] = pygame.transform.smoothscale(img, (size, size))
        return images

    def _show_fixation(self):
        show_fixation(
            self.window,
            self.background_color,
            self.fixation_color,
            self.cfg.get('fixation_time', 2000),
        )

    def _show_stimuli(self) -> int:
        self.window.fill(self.background_color)

        rows = self.cfg['rows']
        cols = self.cfg['cols']
        padding = self.cfg.get('padding', 50)
        angles = self.cfg['angles']

        width, height = self.window.get_size()
        cell_width = (width - 2 * padding) // cols
        cell_height = (height - 2 * padding) // rows

        target_index = random.randint(0, rows * cols - 1)
        target_angle = random.choice(angles)

        for index in range(rows * cols):
            row, col = divmod(index, cols)
            x = padding + col * cell_width + cell_width // 2
            y = padding + row * cell_height + cell_height // 2

            if index == target_index:
                image = pygame.transform.rotate(self.images['T'], target_angle)
            else:
                distractor = random.choice(['L1', 'L2'])
                angle = random.choice(angles)
                image = pygame.transform.rotate(self.images[distractor], angle)

            self.window.blit(image, image.get_rect(center=(x, y)))

        pygame.display.flip()
        return target_angle

    def _wait_response(self, target_angle: int):
        correct_answer = ANGLE_TO_NAME[target_angle]
        timeout = self.cfg.get('response_timeout', 5)
        start = time.time()

        while time.time() - start <= timeout:
            events = pygame.event.get()
            if check_quit(events):
                return None
            for event in events:
                if event.type == pygame.KEYDOWN and event.key in ARROW_KEYS:
                    response = KEY_TO_NAME[event.key]
                    reaction_time = time.time() - start
                    return response, correct_answer, reaction_time

        return 'timeout', correct_answer, timeout

    def get_data_signature(self):
        return {
            'name': 'VSTrial',
            'type': 'none',
            'channel_count': 0,
            'nominal_srate': 0,
            'channel_format': 'string',
            'source_id': f'VS_{self.trial_id}',
        }

    def execute(self):
        self._show_fixation()
        target_angle = self._show_stimuli()
        result = self._wait_response(target_angle)
        if result is None:
            return None
        return result


class VS(GeneralTask):
    """GeneralTask containing a block of VSTrials"""

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.window = create_window(config)
        block = Block('vs_block')

        for trial_idx in range(config['total_trials']):
            trial = VSTrial(trial_id=f'trial_{trial_idx}', parameters=config, window=self.window)
            block.add_trial(trial, order=trial_idx)

        self.add_block(block)

    def execute(self, order: str = 'predefined'):
        self.initial_setup()

        for block in self.blocks:
            block.execute(order)
