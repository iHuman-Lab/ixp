# sensors/individual_differences_mot.py

import pygame
import random
import math
import time
import csv
from pathlib import Path


def run_mot(screen, font, config):
    """
    Multiple Object Tracking (MOT) task.
    Called from main.py.
    Does NOT initialize pygame.
    Uses shared screen, font, and YAML config.
    """

    # -------------------------------------------------
    # GLOBAL CONFIG (shared with VS)
    # -------------------------------------------------
    from configs import WIDTH, HEIGHT
    FPS = 60

    # -------------------------------------------------
    # MOT-SPECIFIC CONFIG
    # -------------------------------------------------
    mot_cfg = config["mot"]

    NUM_OBJECTS = mot_cfg["num_objects"]
    NUM_TARGETS = mot_cfg["num_targets"]
    RADIUS = mot_cfg["radius"]

    N_TRIALS = mot_cfg["n_trials"]
    BASE_SPEED = mot_cfg["base_speed"]
    SPEED_STEP = mot_cfg["speed_step"]

    HIGHLIGHT_TIME = mot_cfg["highlight_time"]
    TRIAL_TIME = mot_cfg["trial_time"]

    OUTPUT_FILE = mot_cfg["output_file"]

    random.seed(mot_cfg.get("random_seed", None))
    clock = pygame.time.Clock()

    # -------------------------------------------------
    # OBJECT CLASS
    # -------------------------------------------------
    class Circle:
        def __init__(self, is_target, speed):
            self.x = random.randint(RADIUS, WIDTH - RADIUS)
            self.y = random.randint(RADIUS, HEIGHT - RADIUS)
            angle = random.uniform(0, 2 * math.pi)
            self.vx = speed * math.cos(angle)
            self.vy = speed * math.sin(angle)
            self.is_target = is_target
            self.selected = False

        def move(self):
            self.x += self.vx
            self.y += self.vy

            if self.x <= RADIUS or self.x >= WIDTH - RADIUS:
                self.vx *= -1
            if self.y <= RADIUS or self.y >= HEIGHT - RADIUS:
                self.vy *= -1

        def draw(self, highlight=False):
            if highlight and self.is_target:
                color = (255, 0, 0)   # target highlight
            elif self.selected:
                color = (0, 255, 0)   # selected
            else:
                color = (200, 200, 200)
            pygame.draw.circle(
                screen, color, (int(self.x), int(self.y)), RADIUS
            )

    # -------------------------------------------------
    # RUN EXPERIMENT
    # -------------------------------------------------
    results = []

    for trial in range(1, N_TRIALS + 1):

        speed = BASE_SPEED + (trial - 1) * SPEED_STEP
        target_indices = random.sample(range(NUM_OBJECTS), NUM_TARGETS)

        circles = [
            Circle(i in target_indices, speed)
            for i in range(NUM_OBJECTS)
        ]

        # -------------------------
        # PHASE 1: HIGHLIGHT
        # -------------------------
        t0 = time.time()
        while time.time() - t0 < HIGHLIGHT_TIME:
            screen.fill((0, 0, 0))
            for c in circles:
                c.draw(highlight=True)
            pygame.display.flip()
            clock.tick(FPS)

        # -------------------------
        # PHASE 2: TRACKING
        # -------------------------
        t0 = time.time()
        while time.time() - t0 < TRIAL_TIME:
            screen.fill((0, 0, 0))
            for c in circles:
                c.move()
                c.draw()
            pygame.display.flip()
            clock.tick(FPS)

        # -------------------------
        # PHASE 3: SELECTION
        # -------------------------
        selected = 0
        selecting = True
        rt_start = time.time()

        while selecting:
            screen.fill((0, 0, 0))
            for c in circles:
                c.draw()

            msg = font.render(
                f"MOT Trial {trial}/{N_TRIALS} – Select {NUM_TARGETS}",
                True,
                (255, 255, 255),
            )
            screen.blit(msg, (20, 20))
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit

                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = pygame.mouse.get_pos()
                    for c in circles:
                        if math.hypot(c.x - mx, c.y - my) <= RADIUS:
                            if not c.selected and selected < NUM_TARGETS:
                                c.selected = True
                                selected += 1
                            elif c.selected:
                                c.selected = False
                                selected -= 1

            if selected == NUM_TARGETS:
                selecting = False

        reaction_time = time.time() - rt_start
        correct = sum(c.is_target and c.selected for c in circles)

        results.append([
            trial,
            speed,
            correct,
            reaction_time
        ])

    # -------------------------------------------------
    # SAVE RESULTS
    # -------------------------------------------------
    out_path = Path(OUTPUT_FILE)
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "trial",
            "speed",
            "correct",
            "reaction_time",
        ])
        writer.writerows(results)
