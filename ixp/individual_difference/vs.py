from __future__ import annotations

import random
import time
from pathlib import Path

import pygame

from ixp.individual_difference.utils import check_quit, create_window, parse_color, save_results, show_fixation
from ixp.task import GeneralTask

MODULE_DIR = Path(__file__).parent

ARROW_KEYS = {pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT}
KEY_TO_NAME = {pygame.K_UP: 'up', pygame.K_DOWN: 'down', pygame.K_LEFT: 'left', pygame.K_RIGHT: 'right'}
ANGLE_TO_NAME = {0: 'up', 90: 'left', 180: 'down', 270: 'right'}


class VS(GeneralTask):
    """Visual Search task: find the T among L distractors."""

    def __init__(self, config: dict):
        super().__init__(config)

        self.cfg = config
        self.window = create_window(config)
        pygame.display.set_caption('Visual Search')
        self.font = pygame.font.Font(None, 80)
        self.images = self._load_images()

        self.background_color = parse_color(config, 'background_color', [120, 120, 120])
        self.fixation_color = parse_color(config, 'fixation_color', [0, 0, 0])

    def _load_images(self) -> dict:
        size = self.cfg.get('stimulus_size', 60)
        images = {}
        for name in ['T', 'L1', 'L2']:
            path = MODULE_DIR / f'{name}.png'
            img = pygame.image.load(str(path)).convert_alpha()
            images[name] = pygame.transform.smoothscale(img, (size, size))
        return images

    def _show_fixation(self) -> None:
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

    def _wait_response(self, target_angle: int) -> tuple[str, str, float] | None:
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

    def execute(self) -> list:
        results = []

        for _ in range(self.cfg['total_trials']):
            self._show_fixation()
            target_angle = self._show_stimuli()
            result = self._wait_response(target_angle)

            if result is None:
                break

            results.append(result)
            pygame.time.delay(self.cfg.get('post_trial_pause', 1000))

        save_results(
            self.cfg.get('output_file', 'vs_results.csv'),
            ['trial', 'response', 'correct_answer', 'rt'],
            [(i + 1, *r) for i, r in enumerate(results)],
        )
        return results
