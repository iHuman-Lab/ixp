import pygame
import random
import time
import csv


# =======================================================
# DRAWING HELPERS
# =======================================================
def draw_text_center(screen, font, text, y, color):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=(screen.get_width() // 2, y))
    screen.blit(rendered, rect)


def draw_fixation(screen, color):
    cx, cy = screen.get_width() // 2, screen.get_height() // 2
    pygame.draw.line(screen, color, (cx, cy - 15), (cx, cy + 15), 3)
    pygame.draw.line(screen, color, (cx - 15, cy), (cx + 15, cy), 3)


def draw_complete_T(surface, x, y, angle, stim_size, color):
    t = pygame.Surface((stim_size, stim_size), pygame.SRCALPHA)
    pygame.draw.rect(t, color, (stim_size * 0.375, 0, stim_size * 0.25, stim_size))
    pygame.draw.rect(t, color, (0, 0, stim_size, stim_size * 0.25))
    surface.blit(pygame.transform.rotate(t, angle), (x, y))


def draw_defective_T(surface, x, y, defect_type, angle, stim_size, color):
    t = pygame.Surface((stim_size, stim_size), pygame.SRCALPHA)
    pygame.draw.rect(t, color, (stim_size * 0.375, 0, stim_size * 0.25, stim_size))

    if defect_type == "┤":
        pygame.draw.rect(t, color, (0, 0, stim_size * 0.25, stim_size * 0.25))
    elif defect_type == "┘":
        pygame.draw.rect(t, color, (stim_size * 0.375, stim_size * 0.75, stim_size * 0.625, stim_size * 0.25))
    elif defect_type == "└":
        pygame.draw.rect(t, color, (0, stim_size * 0.75, stim_size * 0.625, stim_size * 0.25))
    elif defect_type == "┌":
        pygame.draw.rect(t, color, (0, 0, stim_size * 0.625, stim_size * 0.25))

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

    colors = config["colors"]
    timing = config["timing"]
    stimuli = config["stimuli"]

    screen.fill(colors["gray"])
    pygame.display.flip()
    pygame.time.delay(timing["fixation_time"])

    draw_fixation(screen, colors["white"])
    pygame.display.flip()
    pygame.time.delay(timing["isi_time"])

    positions = [
        (
            random.randint(50, screen.get_width() - 50),
            random.randint(50, screen.get_height() - 50),
        )
        for _ in range(num_items)
    ]

    target_idx = random.randint(0, num_items - 1)
    target_angle = random.choice(stimuli["angles"])

    correct_key = {
        0: pygame.K_UP,
        90: pygame.K_LEFT,
        180: pygame.K_DOWN,
        270: pygame.K_RIGHT,
    }[target_angle]

    screen.fill(colors["gray"])

    for i, (x, y) in enumerate(positions):
        if i == target_idx:
            draw_complete_T(
                screen, x, y, target_angle,
                stimuli["stim_size"], colors["black"]
            )
        else:
            draw_defective_T(
                screen, x, y,
                random.choice(stimuli["defective_types"]),
                random.choice(stimuli["angles"]),
                stimuli["stim_size"],
                colors["black"],
            )

    pygame.display.flip()

    response, rt = wait_for_response(timing["response_timeout"])
    return response == correct_key, rt


# =======================================================
# SAVE RESULTS
# =======================================================
def save_results(results, filepath):
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["trial", "difficulty", "num_items", "correct", "rt_ms"])
        writer.writerows(results)


# =======================================================
# TASK ENTRY POINT (USED BY main.py)
# =======================================================
def run_visual_search(screen, font, config):
    """
    Visual Search task.
    Uses ONLY config.yaml. No duplicated parameters.
    """

    colors = config["colors"]
    vs_cfg = config["vs"]
    experiment_cfg = config["experiment"]
    timing = config["timing"]
    files = config["files"]

    wait_for_space(
        screen,
        font,
        [
            "Hello, Welcome to the Visual Search Task",
            "Press SPACE to begin",
        ],
        colors["gray"],
        colors["white"],
    )

    wait_for_space(
        screen,
        font,
        [
            "INSTRUCTIONS",
            "Use arrow keys for orientation",
            "Press SPACE to start",
        ],
        colors["gray"],
        colors["white"],
    )

    results = []
    level_index = 0

    for trial in range(1, vs_cfg["total_trials"] + 1):

        if trial % 10 == 0 and level_index < len(vs_cfg["difficulty_levels"]) - 1:
            level_index += 1

        label, num_items = vs_cfg["difficulty_levels"][level_index]

        correct, rt = run_trial(
            screen=screen,
            config=config,
            num_items=num_items,
        )

        results.append([trial, label, num_items, correct, rt])
        pygame.time.delay(vs_cfg["iti_time"])

    save_results(results, files["results"])
