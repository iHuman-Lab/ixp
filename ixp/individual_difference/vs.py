from __future__ import annotations
 
import csv

import random

import time
 
import pygame
 
from ixp.task import GeneralTask
 
 
class TStimulus(pygame.sprite.Sprite):

    COLOR = (0, 0, 0)

    SELECTED = (0, 200, 0)

    WRONG = (200, 0, 0)
 
    def __init__(

        self,

        is_target: bool,

        angle: int,

        defect_type: str | None,  # "left_short" or "right_short" for distractors; None for target

        x: int,

        y: int,

        size: int,

    ):

        super().__init__()

        self.is_target = is_target

        self.angle = angle

        self.defect_type = defect_type

        self.size = int(size)
 
        self.image_default = self._render(self.COLOR)

        self.image_correct = self._render(self.SELECTED)

        self.image_wrong = self._render(self.WRONG)
 
        self.image = self.image_default

        self.rect = self.image.get_rect(center=(x, y))
 
    def _render(self, color: tuple[int, int, int]) -> pygame.Surface:

        s = self.size
 
        canvas_size = s * 3

        base = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
 
        cx = canvas_size // 2

        cy = canvas_size // 2
 
        thickness = max(4, int(0.20 * s))

        stem_len = int(1.30 * s)

        bar_len = int(1.30 * s)
 
        top_y = cy - stem_len // 2
 
        # vertical stem

        pygame.draw.rect(base, color, pygame.Rect(cx - thickness // 2, top_y, thickness, stem_len))
 
        # horizontal bar at TOP

        if self.is_target:

            left_len = bar_len // 2

            right_len = bar_len // 2

        else:

            short = int(0.25 * bar_len)

            left_len = bar_len // 2

            right_len = bar_len // 2

            if self.defect_type == "left_short":

                left_len = max(thickness, left_len - short)

            elif self.defect_type == "right_short":

                right_len = max(thickness, right_len - short)
 
        pygame.draw.rect(base, color, pygame.Rect(cx - left_len, top_y, left_len, thickness))

        pygame.draw.rect(base, color, pygame.Rect(cx, top_y, right_len, thickness))
 
        rotated = pygame.transform.rotate(base, self.angle)
 
        out = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)

        r = rotated.get_rect(center=(rotated.get_width() // 2, rotated.get_height() // 2))
 
        crop = pygame.Rect(0, 0, s * 2, s * 2)

        crop.center = r.center

        out.blit(rotated, (0, 0), crop)
 
        return out
 
    def mark(self, correct: bool) -> None:

        self.image = self.image_correct if correct else self.image_wrong
 
 
class VisualSearch(GeneralTask):

    def __init__(self, config: dict):

        super().__init__(config)

        pygame.init()
 
        self.config = config

        self.vs = config["vs"]

        self.colors = config.get("colors", {"gray": (120, 120, 120)})
 
        self.window = pygame.display.set_mode((self.vs["width"], self.vs["height"]))

        self.clock = pygame.time.Clock()

        self.stimuli = pygame.sprite.Group()

        self.feedback_ms = 250
 
    def _positions(self, n: int, stim_size: int) -> list[tuple[int, int]]:

        """

        Grid-based positions + jitter.

        - Covers the full screen

        - Prevents overlap (by design)

        """

        w, h = self.window.get_width(), self.window.get_height()
 
        margin = max(80, stim_size * 2)

        usable_w = w - 2 * margin

        usable_h = h - 2 * margin
 
        # choose grid dimensions close to square

        cols = int(n**0.5)

        rows = (n + cols - 1) // cols
 
        cell_w = usable_w // cols

        cell_h = usable_h // rows
 
        # build all grid cells

        cells = [(r, c) for r in range(rows) for c in range(cols)]

        random.shuffle(cells)
 
        positions = []

        half = stim_size  # image is about 2*stim_size wide/high after rendering
 
        # jitter inside each cell (small random move)

        jitter_x = max(2, cell_w // 4)

        jitter_y = max(2, cell_h // 4)
 
        for i in range(n):

            r, c = cells[i]
 
            cx = margin + c * cell_w + cell_w // 2

            cy = margin + r * cell_h + cell_h // 2
 
            x = cx + random.randint(-jitter_x, jitter_x)

            y = cy + random.randint(-jitter_y, jitter_y)
 
            # extra safety clamp so the full symbol stays in frame

            x = max(margin + half, min(w - margin - half, x))

            y = max(margin + half, min(h - margin - half, y))
 
            positions.append((x, y))
 
        return positions
 
    def _create_trial_stimuli(self) -> None:

        self.stimuli.empty()
 
        n = int(self.vs["num_items"])

        size = int(self.vs["stim_size"])

        angles = self.vs["angles"]

        defect_types = self.vs.get("defective_types", ["left_short", "right_short"])
 
        # IMPORTANT: use grid-based positions (no overlap, good coverage)

        positions = self._positions(n, size)
 
        target_idx = random.randint(0, n - 1)
 
        for i, (x, y) in enumerate(positions):

            is_target = (i == target_idx)

            angle = random.choice(angles)
 
            if is_target:

                stim = TStimulus(True, angle, None, x, y, size)

            else:

                stim = TStimulus(False, angle, random.choice(defect_types), x, y, size)
 
            self.stimuli.add(stim)
 
    def _draw(self) -> None:

        self.window.fill(self.colors["gray"])

        self.stimuli.draw(self.window)

        pygame.display.flip()
 
    def single_trial(self):

        timeout = float(self.vs["response_timeout"])

        self._create_trial_stimuli()
 
        start = time.time()

        while time.time() - start < timeout:

            for event in pygame.event.get():

                if event.type == pygame.QUIT:

                    return None
 
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:

                    for s in self.stimuli:

                        if s.rect.collidepoint(event.pos):

                            rt_ms = (time.time() - start) * 1000.0

                            correct = bool(s.is_target)

                            s.mark(correct)

                            self._draw()

                            pygame.time.delay(self.feedback_ms)

                            return correct, rt_ms
 
            self._draw()

            self.clock.tick(60)
 
        return False, None
 
    def execute(self):

        results = []

        total = int(self.vs["total_trials"])

        iti = int(self.vs["iti_time"])
 
        for _ in range(total):

            results.append(self.single_trial())

            pygame.time.delay(iti)
 
        self._save_results(results, self.vs["save_path"])

        return results
 
    @staticmethod

    def _save_results(results, path: str) -> None:

        with open(path, "w", newline="") as f:

            w = csv.writer(f)

            w.writerow(["trial", "correct", "rt_ms"])

            for i, (c, rt) in enumerate(results, 1):

                w.writerow([i, c, rt])

 