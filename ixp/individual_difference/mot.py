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
 
        self.radius = radius

        self.width = width

        self.height = height

        self.is_target = is_target

        self.selected = False

        self.speed = speed
 
        self.image_default = self.make_surface(self.DEFAULT_COLOR)

        self.image_target = self.make_surface(self.TARGET_COLOR)

        self.image_selected = self.make_surface(self.SELECTED_COLOR)
 
        # show targets at the beginning

        self.image = self.image_target if is_target else self.image_default
 
        self.rect = self.image.get_rect(

            center=(

                random.randint(radius, width - radius),

                random.randint(radius, height - radius),

            )

        )
 
        angle = random.uniform(0, 2 * math.pi)

        self.vx = speed * math.cos(angle)

        self.vy = speed * math.sin(angle)
 
    def make_surface(self, color):

        surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)

        pygame.draw.circle(surf, color, (self.radius, self.radius), self.radius)

        return surf
 
    def update(self):

        self.rect.x += self.vx

        self.rect.y += self.vy
 
        if self.rect.left <= 0 or self.rect.right >= self.width:

            self.vx *= -1

        if self.rect.top <= 0 or self.rect.bottom >= self.height:

            self.vy *= -1
 
    def hide_target(self):

        self.image = self.image_default
 
    def select(self):

        self.selected = True

        self.image = self.image_selected
 
 
class MOT(GeneralTask):

    def __init__(self, config):

        super().__init__(config)
 
        pygame.init()

        self.config = config

        self.window = pygame.display.set_mode((config["width"], config["height"]))

        self.clock = pygame.time.Clock()
 
        # 3 targets

        self.target_ids = random.sample(range(config["num_objects"]), 3)
 
        self.circles = pygame.sprite.Group()

        self._create_circles()
 
    def _create_circles(self):

        for i in range(self.config["num_objects"]):

            self.circles.add(

                Circle(

                    i in self.target_ids,

                    self.config["speed"],

                    self.config["radius"],

                    self.window.get_width(),

                    self.window.get_height(),

                )

            )
 
    def single_trial(self):

        # reset selections

        for c in self.circles:

            c.selected = False

            c.image = c.image_target if c.is_target else c.image_default
 
        # show targets first (2 seconds)

        start = pygame.time.get_ticks()

        while pygame.time.get_ticks() - start < 2000:

            self._update_screen()
 
        # hide targets

        for c in self.circles:

            c.hide_target()
 
        # tracking phase

        start = pygame.time.get_ticks()

        while pygame.time.get_ticks() - start < self.config["trial_time"] * 1000:

            self._update_screen()
 
        # selection phase

        selected = []

        while len(selected) < 3:

            for event in pygame.event.get():

                if event.type == pygame.QUIT:

                    pygame.quit()

                    return None

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:

                    for c in self.circles:

                        if c.rect.collidepoint(event.pos):

                            if c not in selected:

                                c.select()

                                selected.append(c)
 
            self._draw()

            self.clock.tick(60)
 
        # compute accuracy (0..3)

        correct = sum(c.is_target for c in selected)

        return correct
 
    def _update_screen(self):

        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                pygame.quit()

                raise SystemExit
 
        self.circles.update()

        self._draw()

        self.clock.tick(60)
 
    def _draw(self):

        self.window.fill((0, 0, 0))

        self.circles.draw(self.window)

        pygame.display.flip()
 
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

 