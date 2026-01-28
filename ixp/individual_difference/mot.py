# mot_task.py
from __future__ import annotations

import math
import random
from typing import Any

import pygame

from ixp.individual_difference.utils import check_quit, create_window, show_fixation
from ixp.task import Block, Task, Trial


class Circle(pygame.sprite.Sprite):
    """
    A moving circle sprite for the MOT task.

    Represents either a target or distractor circle that moves within
    the window bounds and bounces off edges.

    Parameters
    ----------
    is_target : bool
        Whether this circle is a target to track.
    speed : float
        Movement speed in pixels per frame.
    radius : int
        Circle radius in pixels.
    width : int
        Window width for boundary collision.
    height : int
        Window height for boundary collision.

    Attributes
    ----------
    DEFAULT_COLOR : tuple
        RGB color for distractor circles.
    TARGET_COLOR : tuple
        RGB color for target circles.
    SELECTED_COLOR : tuple
        RGB color for selected circles.

    """

    DEFAULT_COLOR = (255, 255, 255)
    TARGET_COLOR = (0, 0, 0)
    SELECTED_COLOR = (0, 0, 0)

    def __init__(self, is_target: bool, speed: float, radius: int, width: int, height: int):
        super().__init__()
        self.radius = radius
        self.width = width
        self.height = height
        self.is_target = is_target
        self.selected = False
        self.speed = speed
        self.moving = False

        # Pre-render images
        self.image_default = self.make_surface(self.DEFAULT_COLOR)
        self.image_target = self.make_surface(self.TARGET_COLOR)
        self.image_selected = self.make_surface(self.SELECTED_COLOR)
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
        if not self.moving:
            return
        self.rect.x += self.vx
        self.rect.y += self.vy
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

    def reset_position(self):
        self.rect.center = (
            random.randint(self.radius, self.width - self.radius),
            random.randint(self.radius, self.height - self.radius),
        )
        angle = random.uniform(0, 2 * math.pi)
        self.vx = self.speed * math.cos(angle)
        self.vy = self.speed * math.sin(angle)


class MOTTrial(Trial):
    """
    Multiple Object Tracking trial implementation.

    Displays moving circles where participants track targets and select
    them after the tracking phase ends.

    Parameters
    ----------
    trial_id : str
        Unique identifier for the trial.
    parameters : dict[str, Any]
        Configuration parameters including num_objects, num_targets, speed, etc.
    window : pygame.Surface
        The pygame window surface to render stimuli.

    """

    def __init__(self, trial_id: str, parameters: dict[str, Any], window: pygame.Surface):
        super().__init__(trial_id, parameters)
        self.cfg = parameters
        self.window = window
        self.clock = pygame.time.Clock()
        self.background_color = self.cfg.get('background_color', [120, 120, 120])
        self.fixation_color = self.cfg.get('fixation_color', [0, 0, 0])
        self.target_ids = set(random.sample(range(self.cfg['num_objects']), self.cfg['num_targets']))
        self.circles = pygame.sprite.Group()
        self._create_circles()

    def _create_circles(self):
        for i in range(self.cfg['num_objects']):
            self.circles.add(
                Circle(
                    is_target=(i in self.target_ids),
                    speed=self.cfg['speed'],
                    radius=self.cfg['radius'],
                    width=self.window.get_width(),
                    height=self.window.get_height(),
                )
            )

    def _update_screen(self, update_motion: bool = True):
        if check_quit():
            raise SystemExit
        if update_motion:
            self.circles.update()
        self.window.fill(self.background_color)
        self.circles.draw(self.window)
        pygame.display.flip()
        self.clock.tick(60)

    def _wait(self, duration_ms: int):
        start = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start < duration_ms:
            self._update_screen(update_motion=False)

    def _reset_circles(self):
        for c in self.circles:
            c.selected = False
            c.moving = False
            c.reset_position()
            c.show_target()

    def _blink_targets(self):
        blink_count = self.cfg.get('blink_count', 3)
        blink_interval = self.cfg.get('blink_interval', 200)
        for _ in range(blink_count):
            for c in self.circles:
                c.hide_target()
            self._wait(blink_interval)
            for c in self.circles:
                c.show_target()
            self._wait(blink_interval)

    def _start_tracking(self):
        for c in self.circles:
            c.hide_target()
            c.moving = True
        tracking_time = self.cfg['trial_time'] * 1000
        start = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start < tracking_time:
            self._update_screen(update_motion=True)
        for c in self.circles:
            c.moving = False

    def _selection_phase(self):
        selected = []
        while len(selected) < self.cfg['num_targets']:
            events = pygame.event.get()
            if check_quit(events):
                return None
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for c in self.circles:
                        if c.rect.collidepoint(event.pos) and c not in selected:
                            c.select()
                            selected.append(c)
            self._update_screen(update_motion=False)
        return selected

    def execute(self):
        # Show fixation
        show_fixation(self.window, self.background_color, self.fixation_color, self.cfg.get('fixation_time', 1000))

        # Reset and display circles
        self._reset_circles()
        self._wait(self.cfg.get('target_display_time', 2000))

        # Blink targets
        self._blink_targets()

        # Tracking phase
        self._start_tracking()

        # Selection phase
        selected = self._selection_phase()
        if selected is None:
            return None

        # Post-trial pause
        self._wait(self.cfg.get('post_trial_pause', 1500))

        # Return number of correctly selected targets
        return sum(c.is_target for c in selected)


class MOT(Task):
    """
    Multiple Object Tracking task containing a block of MOTTrials.

    Participants track a subset of moving circles and select them
    after the tracking phase ends.

    Parameters
    ----------
    config : dict[str, Any]
        Configuration dictionary containing:

        - total_trials : int - Number of trials
        - num_objects : int - Total number of circles
        - num_targets : int - Number of targets to track
        - speed : float - Circle movement speed
        - radius : int - Circle radius
        - trial_time : float - Tracking phase duration in seconds
        - width : int - Window width
        - height : int - Window height

    """

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.window = create_window(config)
        block = Block('mot_block')

        for trial_idx in range(config['total_trials']):
            trial = MOTTrial(trial_id=f'trial_{trial_idx}', parameters=config, window=self.window)
            block.add_trial(trial, order=trial_idx)

        self.add_block(block)

    def execute(self, order: str = 'predefined'):
        if self.blocks:
            for block in self.blocks:
                block.execute(order)
