from __future__ import annotations

import csv
import random
import time

import pygame


def draw_text_center(screen, font, text, y, color):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=(screen.get_width() // 2, y))
    screen.blit(rendered, rect)


def draw_fixation(screen, color):
    cx, cy = screen.get_width() // 2, screen.get_height() // 2
    pygame.draw.line(screen, color, (cx, cy - 15), (cx, cy + 15), 3)
    pygame.draw.line(screen, color, (cx - 15, cy), (cx + 15, cy), 3)


def draw_complete_t(surface, x, y, angle, stim_size, color):
    t = pygame.Surface((stim_size, stim_size), pygame.SRCALPHA)
    pygame.draw.rect(t, color, (stim_size * 0.375, 0, stim_size * 0.25, stim_size))
    pygame.draw.rect(t, color, (0, 0, stim_size, stim_size * 0.25))
    surface.blit(pygame.transform.rotate(t, angle), (x, y))


def draw_defective_T(surface, x, y, defect_type, angle, stim_size, color):
    t = pygame.Surface((stim_size, stim_size), pygame.SRCALPHA)

    # vertical stem
    pygame.draw.rect(t, color, (stim_size * 0.375, 0, stim_size * 0.25, stim_size))

    # only one side of horizontal bar
    if defect_type == 'left':
        pygame.draw.rect(t, color, (0, 0, stim_size * 0.5, stim_size * 0.25))
    elif defect_type == 'right':
        pygame.draw.rect(t, color, (stim_size * 0.5, 0, stim_size * 0.5, stim_size * 0.25))

    surface.blit(pygame.transform.rotate(t, angle), (x, y))


# =======================================================
# UI HELPERS
# =======================================================
def wait_for_space(screen, font, lines, bg_color, text_color):
    while True:
        screen.fill(bg_color)
        for i, line in enumerate(lines):
            draw_text_center(screen, font, line, 150 + i * 50, text_color)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                return


def wait_for_response(timeout):
    start = time.time()
    while time.time() - start < timeout:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                return event.key, (time.time() - start) * 1000
    return None, None


# =======================================================
# SINGLE TRIAL
# =======================================================
def run_trial(screen, config, num_items):
    colors = config['colors']
    timing = config['timing']
    stimuli = config['stimuli']

    screen.fill(colors['gray'])
    pygame.display.flip()
    pygame.time.delay(timing['fixation_time'])

    draw_fixation(screen, colors['white'])
    pygame.display.flip()
    pygame.time.delay(timing['isi_time'])

    # -------- SPATIALLY COVERED, NON-OVERLAPPING DISTRIBUTION --------
    cols = int(num_items**0.5)
    rows = (num_items + cols - 1) // cols

    margin = stimuli.get('margin', 80)

    usable_w = screen.get_width() - 2 * margin
    usable_h = screen.get_height() - 2 * margin

    cell_w = usable_w // cols
    cell_h = usable_h // rows

    # build region list
    cells = []
    for r in range(rows):
        for c in range(cols):
            cells.append((r, c))

    random.shuffle(cells)

    positions = []
    stim_half = stimuli['stim_size'] // 2

    for i in range(num_items):
        r, c = cells[i]

        x_min = margin + c * cell_w + stim_half
        x_max = margin + (c + 1) * cell_w - stim_half
        y_min = margin + r * cell_h + stim_half
        y_max = margin + (r + 1) * cell_h - stim_half

        x = random.randint(x_min, x_max)
        y = random.randint(y_min, y_max)

        positions.append((x, y))
    # ----------------------------------------------------------------

    target_idx = random.randint(0, num_items - 1)
    target_angle = random.choice(stimuli['angles'])

    correct_key = {
        0: pygame.K_UP,
        90: pygame.K_LEFT,
        180: pygame.K_DOWN,
        270: pygame.K_RIGHT,
    }[target_angle]

    screen.fill(colors['gray'])

    defective_types = stimuli['defective_types']

    for i, (x, y) in enumerate(positions):
        if i == target_idx:
            draw_complete_t(
                screen,
                x,
                y,
                target_angle,
                stimuli['stim_size'],
                colors['black'],
            )
        else:
            draw_defective_T(
                screen,
                x,
                y,
                random.choice(defective_types),
                random.choice(stimuli['angles']),
                stimuli['stim_size'],
                colors['black'],
            )

    pygame.display.flip()

    response, rt = wait_for_response(timing['response_timeout'])
    return response == correct_key, rt


def save_results(results, filepath):
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['trial', 'difficulty', 'num_items', 'correct', 'rt_ms'])
        writer.writerows(results)


# =======================================================
# TASK ENTRY POINT
# =======================================================
def run_visual_search(screen, font, config):
    colors = config['colors']
    vs_cfg = config['vs']
    files = config['files']

    wait_for_space(
        screen,
        font,
        ['Hello, Welcome to the Visual Search Task', 'Press SPACE to begin'],
        colors['gray'],
        colors['white'],
    )

    wait_for_space(
        screen,
        font,
        ['INSTRUCTIONS', 'Use arrow keys for orientation', 'Press SPACE to start'],
        colors['gray'],
        colors['white'],
    )

    results = []

    num_trials = vs_cfg['total_trials']
    num_items = vs_cfg['num_items']

    for trial in range(1, num_trials + 1):
        correct, rt = run_trial(
            screen=screen,
            config=config,
            num_items=num_items,
        )

        results.append(
            [
                trial,
                'fixed',
                num_items,
                correct,
                rt,
            ]
        )

        pygame.time.delay(vs_cfg['iti_time'])

    save_results(results, files['results'])
