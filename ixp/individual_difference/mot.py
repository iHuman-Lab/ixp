from __future__ import annotations

import math
import random

import pygame

from ixp.individual_difference.utils import check_quit, create_window, parse_color, save_results, show_fixation
from ixp.task import GeneralTask


class Circle(pygame.sprite.Sprite):
    DEFAULT_COLOR = (255, 255, 255)
    TARGET_COLOR = (0, 0, 0)
    SELECTED_COLOR = (0, 0, 0)

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

    def reset_position(self):
        """Reset circle to a random position with a random velocity."""
        self.rect.center = (
            random.randint(self.radius, self.width - self.radius),
            random.randint(self.radius, self.height - self.radius),
        )
        angle = random.uniform(0, 2 * math.pi)
        self.vx = self.speed * math.cos(angle)
        self.vy = self.speed * math.sin(angle)


class MOT(GeneralTask):
    def __init__(self, config):
        super().__init__(config)

        self.cfg = config
        self.window = create_window(config)
        pygame.display.set_caption('Multiple Object Tracking')

        self.clock = pygame.time.Clock()

        self.background_color = parse_color(config, 'background_color', [120, 120, 120])
        self.fixation_color = parse_color(config, 'fixation_color', [0, 0, 0])

        # targets
        self.target_ids = set(random.sample(range(config['num_objects']), config['num_targets']))
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

        self._draw()
        self.clock.tick(60)

    def _draw(self):
        self.window.fill(self.background_color)
        self.circles.draw(self.window)
        pygame.display.flip()

    def _show_fixation(self):
        show_fixation(
            self.window,
            self.background_color,
            self.fixation_color,
            self.cfg.get('fixation_time', 1000),
        )

    def _wait(self, duration_ms):
        """Wait for a specified duration while updating the screen."""
        start = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start < duration_ms:
            self._update_screen(update_motion=False)

    def _reset_circles(self):
        """Reset all circles to random positions with targets visible."""
        for c in self.circles:
            c.selected = False
            c.moving = False
            c.reset_position()
            c.show_target()

    def _blink_targets(self):
        """Blink targets to signal upcoming movement."""
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
        """Hide targets and start movement for tracking phase."""
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
        """Handle user selection of targets. Returns list of selected circles."""
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
            self._draw()
            self.clock.tick(60)
        return selected

    def single_trial(self):
        self._show_fixation()
        self._reset_circles()
        self._wait(self.cfg.get('target_display_time', 2000))
        self._blink_targets()
        self._start_tracking()
        selected = self._selection_phase()
        if selected is None:
            return None
        self._wait(self.cfg.get('post_trial_pause', 1500))
        return sum(c.is_target for c in selected)

    def execute(self):
        results = []

        for trial in range(1, self.cfg['total_trials'] + 1):
            correct = self.single_trial()
            if correct is None:
                break
            results.append((trial, correct))

        save_results(
            self.cfg.get('output_file', 'mot_results.csv'),
            ['trial', 'num_correct'],
            results,
        )

        return results
