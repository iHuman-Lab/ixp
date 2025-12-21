from __future__ import annotations

import math
import random

import pygame

from ixp.task import GeneralTask


class Circle(pygame.sprite.Sprite):
    """Optimized sprite representing a moving circle in MOT task."""

    # Color constants
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

        # Pre-render all states for performance
        self.image_default = self._create_circle_surface(self.DEFAULT_COLOR)
        self.image_selected = self._create_circle_surface(self.SELECTED_COLOR)
        self.image_target = self._create_circle_surface(self.TARGET_COLOR)
        self.image = self.image_default

        # Initialize position
        self.rect = self.image.get_rect(
            center=(
                random.randint(radius, width - 2 * radius),
                random.randint(radius, height - 2 * radius),
            )
        )

        # Initialize velocity with random angle
        angle = random.uniform(-math.pi, math.pi)
        self.vx = speed * math.cos(angle)
        self.vy = speed * math.sin(angle)

    def _create_circle_surface(self, color: tuple[int, int, int]) -> pygame.Surface:
        """Create a circular surface with the given color."""
        diameter = self.radius * 2
        surf = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, (self.radius, self.radius), self.radius)
        return surf

    def update(self) -> None:
        """Update circle position and handle boundary collisions."""
        # Update position
        self.rect.x += self.vx
        self.rect.y += self.vy

        # Bounce off walls
        if self.rect.left <= 0 or self.rect.right >= self.width:
            self.vx = -self.vx
            # Clamp position to prevent getting stuck
            self.rect.clamp_ip(pygame.Rect(0, 0, self.width, self.height))

        if self.rect.top <= 0 or self.rect.bottom >= self.height:
            self.vy = -self.vy
            self.rect.clamp_ip(pygame.Rect(0, 0, self.width, self.height))

    def set_state(self, highlight: bool = False) -> None:  # noqa: FBT001
        """Update circle appearance based on current state."""
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

        # Set random seed before generating targets
        self.target_indices = random.sample(range(config['num_objects']), config['num_targets'])

        self.circles: pygame.sprite.Group = self._create_circles()

    def _create_circles(self) -> pygame.sprite.Group:
        """Create all circle sprites for the task."""
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
        """Run a single trial of the MOT task."""
        running = True
        black = (0, 0, 0)

        while running:
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # Update all circles
            self.circles.update()

            # Render
            self.window.fill(black)
            self.circles.draw(self.window)
            pygame.display.flip()

            # Maintain 60 FPS
            self.clock.tick(60)

    def execute(self) -> list:
        """Execute the MOT task and return results."""
        results = []
        self.single_trial()

        # TODO: Implement Phase 2 (tracking) and Phase 3 (selection)
        # TODO: Implement result collection and saving

        return results
