import pygame
import yaml
from pathlib import Path

from sensors.individual_differences_vs import *

from utils import skip_run
from configs import WIDTH, HEIGHT, TOTAL_TRIALS, DIFFICULTY_LEVELS, ITI_TIME



# -------------------------------------------------
# CONFIG PATH (explicit YAML usage)
# -------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = ROOT_DIR / "configs" / "config.yaml"

with skip_run("run", "load_config") as check:
    if check():
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)


def main():

    # -------------------------------
    # INIT
    # -------------------------------
    with skip_run("run", "init_pygame") as check:
        if check():
            screen, font = init_pygame()

            try:
                correct_sound = pygame.mixer.Sound(CORRECT_SOUND_FILE)
            except:
                correct_sound = None


    # -------------------------------
    # START MENU
    # -------------------------------
    with skip_run("run", "start_menu") as check:
        if check():
            wait_for_space(
                screen,
                font,
                [
                    "VISUAL SEARCH TASK",
                    "Press SPACE to begin",
                ],
            )


    # -------------------------------
    # INSTRUCTIONS
    # -------------------------------
    with skip_run("run", "instructions") as check:
        if check():
            wait_for_space(
                screen,
                font,
                [
                    "INSTRUCTIONS",
                    "Find the complete T",
                    "Use arrow keys for orientation",
                    "Press SPACE to start",
                ],
            )


    # -------------------------------
    # MAIN EXPERIMENT LOOP
    # -------------------------------
    results = []
    level_index = 0

    with skip_run("run", "experiment") as check:
        if check():
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


    # -------------------------------
    # SAVE RESULTS
    # -------------------------------
    with skip_run("run", "save_results") as check:
        if check():
            save_results(results)


    # -------------------------------
    # END SCREEN
    # -------------------------------
    with skip_run("run", "end_screen") as check:
        if check():
            screen.fill(GRAY)
            draw_text(screen, font, "Task Complete", 250)
            draw_text(screen, font, f"Saved: {RESULTS_FILE}", 320)
            pygame.display.flip()
            pygame.time.delay(3000)
            pygame.quit()


if __name__ == "__main__":
    main()
