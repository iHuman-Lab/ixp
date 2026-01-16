from __future__ import annotations

import csv
import os
from pathlib import Path

import pygame


def create_window(config: dict) -> pygame.Surface:
    """
    Create a pygame window based on config settings.

    Supports fullscreen mode and centers the window on screen.

    Args:
        config: Dictionary with 'width', 'height', and optional 'fullscreen' keys.

    Returns:
        pygame.Surface: The created window surface.

    """
    pygame.init()

    if config.get('fullscreen', False):
        window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        width = config['width']
        height = config['height']

        # Center the window on screen
        screen_info = pygame.display.Info()
        x = (screen_info.current_w - width) // 2
        y = (screen_info.current_h - height) // 2

        os.environ['SDL_VIDEO_WINDOW_POS'] = f'{x},{y}'

        window = pygame.display.set_mode((width, height))

    return window


def show_fixation(
    window: pygame.Surface,
    background_color: tuple,
    fixation_color: tuple,
    duration_ms: int,
    font_size: int = 80,
) -> None:
    """
    Display a fixation cross on the screen.

    Args:
        window: The pygame window surface.
        background_color: RGB tuple for background.
        fixation_color: RGB tuple for the fixation cross.
        duration_ms: How long to display the fixation in milliseconds.
        font_size: Size of the fixation cross font.

    """
    window.fill(background_color)
    font = pygame.font.Font(None, font_size)
    text = font.render('+', True, fixation_color)
    window.blit(text, text.get_rect(center=window.get_rect().center))
    pygame.display.flip()
    pygame.time.delay(duration_ms)


def save_results(filepath: str, headers: list, rows: list) -> None:
    """
    Save results to a CSV file.

    Args:
        filepath: Path to the output CSV file.
        headers: List of column headers.
        rows: List of row data (each row is a tuple/list).

    """
    out = Path(filepath)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def parse_color(config: dict, key: str, default: list) -> tuple:
    """
    Parse a color from config, converting list to tuple.

    Args:
        config: Configuration dictionary.
        key: Key to look up in config.
        default: Default RGB list if key not found.

    Returns:
        RGB tuple.

    """
    return tuple(config.get(key, default))


def check_quit(events: list | None = None) -> bool:
    """
    Check if user requested to quit.

    Args:
        events: Optional list of pygame events. If None, fetches events.

    Returns:
        True if quit was requested, False otherwise.

    """
    if events is None:
        events = pygame.event.get()

    for event in events:
        if event.type == pygame.QUIT:
            pygame.quit()
            return True
    return False
