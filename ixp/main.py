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

    # ---------------- VISUAL SEARCH ----------------
    with skip_run("skip", "visual_search") as check:
        if check():
            run_visual_search(
                screen=screen,
                font=font,
                config=config
            )

    # ---------------- MOT ----------------
    with skip_run("run", "mot_task") as check:
        if check():
            run_mot(
                screen=screen,
                font=font,
                config=config
            )

    pygame.quit()


if __name__ == "__main__":
    main()
