from __future__ import annotations

import random
import time
from typing import List

import pygame

from ixp.task import GeneralTask


# -----------------------------------------------------
# Stimulus helpers
# -----------------------------------------------------
class TStimulus:
    @staticmethod
    def draw_complete(
        surface, center, angle, size, color
    ) -> None:
        t = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(t, color, (size * 0.375, 0, size * 0.25, size))
        pygame.draw.rect(t, color, (0, 0, size, size * 0.25))
        t = pygame.transform.rotate(t, angle)
        rect = t.get_rect(center=center)
        surface.blit(t, rect)

    @staticmethod
    def draw_defective(
        surface, center, defect_type, angle, size, color
    ) -> None:
        t = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(t, color, (size * 0.375, 0, size * 0.25, size))

        if defect_type == "left":
            pygame.draw.rect(t, color, (0, 0, size * 0.5, size * 0.25))
        elif defect_type == "right":
            pygame.draw.rect(t, color, (size * 0.5, 0, size * 0.5, size * 0.25))

        t = pygame.transform.rotate(t, angle)
        rect = t.get_rect(center=center)
        surface.blit(t, rect)


# -----------------------------------------------------
# Visual Search task
# -----------------------------------------------------
class VisualSearch(GeneralTask):
    """Visual Search task (MOT-style, YAML-aligned)."""

    def __init__(self, config: dict) -> None:
        super().__init__(config)

        pygame.init()

        self.cfg = config["vs"]
        self.colors = config["colors"]

        self.window = pygame.display.set_mode(
            (self.cfg["width"], self.cfg["height"])
        )
        self.clock = pygame.time.Clock()

    # -------------------------------------------------
    # UI phases
    # -------------------------------------------------
    def _wait_for_space(self, lines: list[str]) -> None:
        font = pygame.font.SysFont(None, 36)

        while True:
            self.window.fill(self.colors["gray"])
            for i, line in enumerate(lines):
                rendered = font.render(line, True, self.colors["white"])
                rect = rendered.get_rect(
                    center=(self.cfg["width"] // 2, 150 + i * 50)
                )
                self.window.blit(rendered, rect)

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    return

    def _draw_fixation(self) -> None:
        self.window.fill(self.colors["gray"])
        cx, cy = self.cfg["width"] // 2, self.cfg["height"] // 2

        pygame.draw.line(
            self.window, self.colors["white"], (cx, cy - 15), (cx, cy + 15), 3
        )
        pygame.draw.line(
            self.window, self.colors["white"], (cx - 15, cy), (cx + 15, cy), 3
        )

        pygame.display.flip()
        pygame.time.delay(self.cfg["fixation_time"])

    # -------------------------------------------------
    # Trial construction
    # -------------------------------------------------
    def _build_positions(self, n_items: int) -> list[tuple[int, int]]:
        cols = int(n_items ** 0.5)
        rows = (n_items + cols - 1) // cols

        margin = 80
        usable_w = self.cfg["width"] - 2 * margin
        usable_h = self.cfg["height"] - 2 * margin

        cell_w = usable_w // cols
        cell_h = usable_h // rows

        cells = [(r, c) for r in range(rows) for c in range(cols)]
        random.shuffle(cells)

        positions = []
        half = self.cfg["stim_size"] // 2

        for i in range(n_items):
            r, c = cells[i]
            x = random.randint(
                margin + c * cell_w + half,
                margin + (c + 1) * cell_w - half,
            )
            y = random.randint(
                margin + r * cell_h + half,
                margin + (r + 1) * cell_h - half,
            )
            positions.append((x, y))

        return positions

    # -------------------------------------------------
    # Trial execution
    # -------------------------------------------------
    def _run_trial(self, n_items: int) -> tuple[bool, float]:
        self._draw_fixation()
        pygame.time.delay(self.cfg["isi_time"])

        positions = self._build_positions(n_items)

        target_idx = random.randint(0, n_items - 1)
        target_angle = random.choice(self.cfg["angles"])

        correct_key = {
            0: pygame.K_UP,
            90: pygame.K_LEFT,
            180: pygame.K_DOWN,
            270: pygame.K_RIGHT,
        }[target_angle]

        self.window.fill(self.colors["gray"])

        for i, pos in enumerate(positions):
            if i == target_idx:
                TStimulus.draw_complete(
                    self.window,
                    pos,
                    target_angle,
                    self.cfg["stim_size"],
                    self.colors["black"],
                )
            else:
                TStimulus.draw_defective(
                    self.window,
                    pos,
                    random.choice(self.cfg["defective_types"]),
                    random.choice(self.cfg["angles"]),
                    self.cfg["stim_size"],
                    self.colors["black"],
                )

        pygame.display.flip()

        start = time.time()
        while time.time() - start < self.cfg["response_timeout"]:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit
                if event.type == pygame.KEYDOWN:
                    rt = (time.time() - start) * 1000
                    return event.key == correct_key, rt

        return False, None

    # -------------------------------------------------
    # Task execution
    # -------------------------------------------------
    def execute(self) -> List[dict]:
        self._wait_for_space(
            ["Hello, Welcome to the Visual Search Task", "Press SPACE to begin"]
        )

        self._wait_for_space(
            ["INSTRUCTIONS", "Use arrow keys for orientation", "Press SPACE to start"]
        )

        results = []

        for trial in range(self.cfg["total_trials"]):
            correct, rt = self._run_trial(self.cfg["num_items"])

            results.append(
                {
                    "trial": trial,
                    "num_items": self.cfg["num_items"],
                    "correct": correct,
                    "rt_ms": rt,
                }
            )

            pygame.time.delay(self.cfg["iti_time"])

        pygame.display.quit()
        pygame.quit()
        return results
