from __future__ import annotations

import csv
import random
import time
from pathlib import Path

import pygame

from ixp.task import GeneralTask

MODULE_DIR = Path(__file__).parent

ARROW_KEYS = {pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT}
KEY_TO_NAME = {pygame.K_UP: 'up', pygame.K_DOWN: 'down', pygame.K_LEFT: 'left', pygame.K_RIGHT: 'right'}
ANGLE_TO_NAME = {0: 'up', 90: 'left', 180: 'down', 270: 'right'}

GRAY = (120, 120, 120)
BLACK = (0, 0, 0)


class VS(GeneralTask):
    """Visual Search task: find the T among L distractors."""

    def __init__(self, config: dict):
        super().__init__(config)
        pygame.init()

        self.cfg = config
        self.window = pygame.display.set_mode((config['width'], config['height']))
        self.font = pygame.font.Font(None, 80)
        self.images = self._load_images()

    def _load_images(self) -> dict:
        size = self.cfg.get('stimulus_size', 60)
        images = {}
        for name in ['T', 'L1', 'L2']:
            path = MODULE_DIR / f'{name}.png'
            img = pygame.image.load(str(path)).convert_alpha()
            images[name] = pygame.transform.smoothscale(img, (size, size))
        return images

    def _show_fixation(self) -> None:
        self.window.fill(GRAY)
        text = self.font.render('+', True, BLACK)
        self.window.blit(text, text.get_rect(center=self.window.get_rect().center))
        pygame.display.flip()
        pygame.time.delay(self.cfg.get('fixation_time', 2000))

    def _show_stimuli(self) -> int:
        self.window.fill(GRAY)

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
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN and event.key in ARROW_KEYS:
                    response = KEY_TO_NAME[event.key]
                    reaction_time = time.time() - start
                    return response, correct_answer, reaction_time

        return 'timeout', correct_answer, timeout

    def _save_results(self, results: list) -> None:
        with open(self.cfg['save_path'], 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['trial', 'response', 'correct_answer', 'rt'])
            for trial_num, (response, correct_answer, rt) in enumerate(results, 1):
                writer.writerow([trial_num, response, correct_answer, rt])

    def execute(self) -> list:
        results = []

        for _ in range(self.cfg['total_trials']):
            self._show_fixation()
            target_angle = self._show_stimuli()
            result = self._wait_response(target_angle)

            if result is None:
                break

            results.append(result)
            pygame.time.delay(self.cfg.get('iti_time', 1000))

        self._save_results(results)
        return results
