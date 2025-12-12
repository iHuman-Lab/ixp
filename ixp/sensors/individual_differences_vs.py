
import pygame
import random
import time
import csv
from configs import *
from configs import WHITE, BLACK, GRAY




# -------------------------------------------------------
# INIT
# -------------------------------------------------------
def init_pygame():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Visual Search Task")
    font = pygame.font.SysFont(None, 40)
    return screen, font


# -------------------------------------------------------
# DRAWING
# -------------------------------------------------------
def draw_text(screen, font, text, y, color=WHITE):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=(WIDTH // 2, y))
    screen.blit(rendered, rect)


def draw_complete_T(surface, x, y, angle):
    t = pygame.Surface((STIM_SIZE, STIM_SIZE), pygame.SRCALPHA)
    pygame.draw.rect(t, BLACK, (15, 0, 10, 40))
    pygame.draw.rect(t, BLACK, (0, 0, 40, 10))
    rotated = pygame.transform.rotate(t, angle)
    surface.blit(rotated, (x, y))


def draw_defective_T(surface, x, y, defect_type, angle):
    t = pygame.Surface((STIM_SIZE, STIM_SIZE), pygame.SRCALPHA)

    if defect_type == "┤":
        pygame.draw.rect(t, BLACK, (15, 0, 10, 40))
        pygame.draw.rect(t, BLACK, (0, 0, 10, 10))
    elif defect_type == "┘":
        pygame.draw.rect(t, BLACK, (15, 0, 10, 40))
        pygame.draw.rect(t, BLACK, (15, 30, 25, 10))
    elif defect_type == "└":
        pygame.draw.rect(t, BLACK, (15, 0, 10, 40))
        pygame.draw.rect(t, BLACK, (0, 30, 25, 10))
    elif defect_type == "┌":
        pygame.draw.rect(t, BLACK, (15, 0, 10, 40))
        pygame.draw.rect(t, BLACK, (0, 0, 25, 10))

    rotated = pygame.transform.rotate(t, angle)
    surface.blit(rotated, (x, y))


# -------------------------------------------------------
# MENUS
# -------------------------------------------------------
def wait_for_space(screen, font, lines):
    waiting = True
    while waiting:
        screen.fill(GRAY)
        for i, line in enumerate(lines):
            draw_text(screen, font, line, 150 + i * 50)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); quit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                waiting = False


# -------------------------------------------------------
# SINGLE TRIAL
# -------------------------------------------------------
def run_trial(screen, num_items, correct_sound):
    screen.fill(GRAY)
    pygame.display.flip()

    pygame.time.delay(FIXATION_TIME)
    pygame.draw.line(screen, WHITE, (400, 285), (400, 315), 3)
    pygame.draw.line(screen, WHITE, (385, 300), (415, 300), 3)
    pygame.display.flip()
    pygame.time.delay(ISI_TIME)

    positions = [(random.randint(50, 750), random.randint(50, 550))
                 for _ in range(num_items)]

    target_idx = random.randint(0, num_items - 1)
    target_angle = random.choice(ANGLES)

    correct_key = {
        0: pygame.K_UP,
        90: pygame.K_LEFT,
        180: pygame.K_DOWN,
        270: pygame.K_RIGHT
    }[target_angle]

    screen.fill(GRAY)

    for i, (x, y) in enumerate(positions):
        if i == target_idx:
            draw_complete_T(screen, x, y, target_angle)
        else:
            draw_defective_T(
                screen,
                x,
                y,
                random.choice(DEFECTIVE_TYPES),
                random.choice(ANGLES)
            )

    pygame.display.flip()

    start = time.time()
    response = None
    rt = None

    while time.time() - start < RESPONSE_TIMEOUT:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); quit()
            if event.type == pygame.KEYDOWN:
                response = event.key
                rt = (time.time() - start) * 1000
                break
        if response:
            break

    correct = response == correct_key
    if correct and correct_sound:
        correct_sound.play()

    return correct, rt


# -------------------------------------------------------
# SAVE RESULTS
# -------------------------------------------------------
def save_results(results):
    with open(RESULTS_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["trial", "difficulty", "num_items", "correct", "rt_ms"])
        writer.writerows(results)
