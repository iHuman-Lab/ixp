from __future__ import annotations

import csv
import math
import random
from pathlib import Path

import pygame

from ixp.task import GeneralTask


class Circle(pygame.sprite.Sprite):
    DEFAULT_COLOR = (200, 200, 200)
    TARGET_COLOR = (255, 0, 0)
    SELECTED_COLOR = (0, 255, 0)

    def __init__(self, is_target, speed, radius, width, height):
        super().__init__()

        self.radius = int(radius)
        self.width = int(width)
        self.height = int(height)
        self.is_target = bool(is_target)

        self.selected = False
        self.speed = float(speed)

        # motion control
        self.moving = False  # start stable (no movement)

        # pre-render images
        self.image_default = self.make_surface(self.DEFAULT_COLOR)
        self.image_target = self.make_surface(self.TARGET_COLOR)
        self.image_selected = self.make_surface(self.SELECTED_COLOR)

        # show targets at the beginning
        self.image = self.image_target if self.is_target else self.image_default

        self.rect = self.image.get_rect(
            center=(
                random.randint(self.radius, self.width - self.radius),
                random.randint(self.radius, self.height - self.radius),
            )
        )

        angle = random.uniform(0, 2 * math.pi)
        self.vx = self.speed * math.cos(angle)
        self.vy = self.speed * math.sin(angle)

    def make_surface(self, color):
        surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, (self.radius, self.radius), self.radius)
        return surf

    def update(self):
        # Do not move during the stable phase
        if not self.moving:
            return

        self.rect.x += self.vx
        self.rect.y += self.vy

        # bounce
        if self.rect.left <= 0 or self.rect.right >= self.width:
            self.vx *= -1
        if self.rect.top <= 0 or self.rect.bottom >= self.height:
            self.vy *= -1

    def hide_target(self):
        self.image = self.image_default

    def show_target(self):
        self.image = self.image_target if self.is_target else self.image_default

    def select(self):
        self.selected = True
        self.image = self.image_selected


class MOT(GeneralTask):
    def __init__(self, config):
        super().__init__(config)

        pygame.init()
        self.config = config

        self.window = pygame.display.set_mode((config["width"], config["height"]))
        pygame.display.set_caption("MOT")

        self.clock = pygame.time.Clock()

        # 3 targets
        self.target_ids = set(random.sample(range(config["num_objects"]), 3))
        self.circles = pygame.sprite.Group()
        self._create_circles()

    def _create_circles(self):
        for i in range(self.config["num_objects"]):
            self.circles.add(
                Circle(
                    is_target=(i in self.target_ids),
                    speed=self.config["speed"],
                    radius=self.config["radius"],
                    width=self.window.get_width(),
                    height=self.window.get_height(),
                )
            )

    def _update_screen(self, update_motion: bool = True):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

        if update_motion:
            self.circles.update()

        self._draw()
        self.clock.tick(60)

    def _draw(self):
        self.window.fill((0, 0, 0))
        self.circles.draw(self.window)
        pygame.display.flip()

    def single_trial(self):
        # reset selections + show targets, but keep them stable
        for c in self.circles:
            c.selected = False
            c.moving = False
            c.show_target()

        # Phase 1: show targets for 2 seconds (STABLE)
        start = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start < 2000:
            self._update_screen(update_motion=False)

        # Immediately hide targets AND start movement
        for c in self.circles:
            c.hide_target()
            c.moving = True

        # Phase 2: tracking phase (MOVING)
        start = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start < self.config["trial_time"] * 1000:
            self._update_screen(update_motion=True)

        # Freeze for selection phase (recommended)
        for c in self.circles:
            c.moving = False

        # Phase 3: selection phase
        selected = []
        while len(selected) < 3:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return None

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for c in self.circles:
                        if c.rect.collidepoint(event.pos) and c not in selected:
                            c.select()
                            selected.append(c)

            self._draw()
            self.clock.tick(60)

        return sum(c.is_target for c in selected)

    def execute(self):
        results = []

        for trial in range(1, self.config["n_trials"] + 1):
            correct = self.single_trial()
            results.append((trial, correct))

        # SAVE RESULTS
        out = self.config.get("output_file", "mot_results.csv")
        Path(out).parent.mkdir(parents=True, exist_ok=True)

        with open(out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["trial", "num_correct_out_of_3"])
            w.writerows(results)

        return results
