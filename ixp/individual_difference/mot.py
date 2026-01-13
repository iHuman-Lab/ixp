from __future__ import annotations
 
import math

import random
 
import pygame
 
from ixp.task import GeneralTask
 
 
class Circle(pygame.sprite.Sprite):

    """Optimized sprite representing a moving circle in MOT task."""
 
    DEFAULT_COLOR = (200, 200, 200)

    SELECTED_COLOR = (0, 255, 0)

    TARGET_COLOR = (255, 0, 0)
 
    __slots__ = (

        'height',

        'image',

        'image_default',

        'image_selected',

        'image_target',

        'is_target',

        'radius',

        'rect',

        'selected',

        'speed',

        'vx',

        'vy',

        'width',

    )
 
    def __init__(self, is_target: bool, speed: float, radius: int, width: int, height: int) -> None:

        super().__init__()

        self.radius = radius

        self.width = width

        self.height = height

        self.is_target = is_target

        self.selected = False

        self.speed = speed
 
        self.image_default = self._create_circle_surface(self.DEFAULT_COLOR)

        self.image_selected = self._create_circle_surface(self.SELECTED_COLOR)

        self.image_target = self._create_circle_surface(self.TARGET_COLOR)

        self.image = self.image_default
 
        self.rect = self.image.get_rect(

            center=(

                random.randint(radius, width - 2 * radius),

                random.randint(radius, height - 2 * radius),

            )

        )
 
        angle = random.uniform(-math.pi, math.pi)

        self.vx = speed * math.cos(angle)

        self.vy = speed * math.sin(angle)
 
    def _create_circle_surface(self, color: tuple[int, int, int]) -> pygame.Surface:

        diameter = self.radius * 2

        surf = pygame.Surface((diameter, diameter), pygame.SRCALPHA)

        pygame.draw.circle(surf, color, (self.radius, self.radius), self.radius)

        return surf
 
    def update(self) -> None:

        self.rect.x += self.vx

        self.rect.y += self.vy
 
        if self.rect.left <= 0 or self.rect.right >= self.width:

            self.vx = -self.vx

            self.rect.clamp_ip(pygame.Rect(0, 0, self.width, self.height))
 
        if self.rect.top <= 0 or self.rect.bottom >= self.height:

            self.vy = -self.vy

            self.rect.clamp_ip(pygame.Rect(0, 0, self.width, self.height))
 
    def set_state(self, highlight: bool = False) -> None:

        if highlight and self.is_target:

            self.image = self.image_target

        elif self.selected:

            self.image = self.image_selected

        else:

            self.image = self.image_default
 
 
class MOT(GeneralTask):

    """Multiple Object Tracking task implementation."""
 
    def __init__(self, config: dict) -> None:

        super().__init__(config)

        pygame.init()

        self.config = config

        self.window = pygame.display.set_mode((config['width'], config['height']))

        self.clock = pygame.time.Clock()
 
        self.target_indices = random.sample(range(config['num_objects']), config['num_targets'])

        self.circles: pygame.sprite.Group = self._create_circles()
 
    def _create_circles(self) -> pygame.sprite.Group:

        circles = pygame.sprite.Group()

        for i in range(self.config['num_objects']):

            circle = Circle(

                is_target=i in self.target_indices,

                speed=self.config['speed'],

                radius=self.config['radius'],

                width=self.window.get_width(),

                height=self.window.get_height(),

            )

            circles.add(circle)

        return circles
 
    def single_trial(self) -> None:

        black = (0, 0, 0)
 
        start_time = pygame.time.get_ticks()

        while (pygame.time.get_ticks() - start_time) < self.config["trial_time"] * 1000:
 
            for event in pygame.event.get():

                if event.type == pygame.QUIT:

                    return
 
            self.circles.update()
 
            self.window.fill(black)

            self.circles.draw(self.window)

            pygame.display.flip()
 
            self.clock.tick(60)
 
    def execute(self) -> list:

        results = []
 
        for _ in range(self.config["n_trials"]):

            self.single_trial()
 
        return results

 