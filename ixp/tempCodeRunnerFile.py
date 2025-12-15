# main.py

import pygame
import yaml
from pathlib import Path

from sensors.individual_differences_vs import run_visual_search

from sensors.individual_differences_mot import run_mot
from utils import skip_run
from configs import WIDTH, HEIGHT

# -------------------------------------------------
# LOAD CONFIGS
# -------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent

with open(ROOT_DIR / "configs" / "config.yaml") as f:
    config = yaml.safe_load(f)

with open(ROOT_DIR / "configs" / "mot.config.yaml") as f:
    mot_cfg = yaml.safe_load(f)

config.update(mot_cfg)  # merge safely

def main():

    # ---------------- INIT ----------------
    with skip_run("run", "init_pygame") as check:
        if check():
            pygame.init()
            screen = pygame.display.set_mode((WIDTH, HEIGHT))
            pygame.display.set_caption("IXP Tasks")
            font = pygame.font.SysFont(None, 40)

            try:
                correct_sound = pygame.mixer.Sound(CORRECT_SOUND_FILE)
            except:
                correct_sound = None

    # ---------------- VISUAL SEARCH ----------------
    with skip_run("run", "visual_search") as check:
        if check():

            # START MENU
            wait_for_space(
                screen,
                font,
                [
                    "Hello, Welcome to the Visual Search Task",
                    "Press SPACE to begin",
                ],
            )

            # INSTRUCTIONS
            wait_for_space(
                screen,
                font,
                [
                    "INSTRUCTIONS",
                    "Use arrow keys for orientation",
                    "Press SPACE to start",
                ],
            )

            # MAIN VS LOOP
            results = []
            level_index = 0

            for trial in range(1, TOTAL_TRIALS + 1):

                if trial % 10 == 0 and level_index < len(DIFFICULTY_LEVELS) - 1:
                    level_index += 1

                label, num_items = DIFFICULTY_LEVELS[level_index]

                correct, rt = run_trial(
                    screen=screen,
                    num_items=num_items,
                    correct_sound=correct_sound,
                )

                results.append([trial, label, num_items, correct, rt])
                pygame.time.delay(ITI_TIME)

            save_results(results)

    # ---------------- MOT ----------------
    with skip_run("skip", "mot_task") as check:
        if check():
            run_mot(screen, font, config)

    pygame.quit()


if __name__ == "__main__":
    main()
