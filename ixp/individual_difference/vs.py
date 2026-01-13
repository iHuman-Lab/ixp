from __future__ import annotations
 
import random
import time
import pygame
 
from ixp.task import GeneralTask
 
 
# ======================================================
# VISUAL SEARCH STIMULUS (like Circle in MOT)
# ======================================================
 
class TStimulus(pygame.sprite.Sprite):
    DEFAULT_COLOR = (0, 0, 0)
 
    def __init__(self, is_target, angle, defect_type, x, y, size):
        super().__init__()
        self.is_target = is_target
        self.angle = angle
        self.defect_type = defect_type
        self.size = size
 
        self.image = self._make_image()
        self.rect = self.image.get_rect(center=(x, y))
 
    def _make_image(self):
        surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
 
        # vertical bar
        pygame.draw.rect(surf, self.DEFAULT_COLOR,
                         (self.size * 0.375, 0, self.size * 0.25, self.size))
 
        # horizontal bar
        if self.is_target:
            pygame.draw.rect(surf, self.DEFAULT_COLOR,
                             (0, 0, self.size, self.size * 0.25))
        else:
            if self.defect_type == "left":
                pygame.draw.rect(surf, self.DEFAULT_COLOR,
                                 (0, 0, self.size * 0.5, self.size * 0.25))
            else:
                pygame.draw.rect(surf, self.DEFAULT_COLOR,
                                 (self.size * 0.5, 0, self.size * 0.5, self.size * 0.25))
 
        return pygame.transform.rotate(surf, self.angle)
 
 
# ======================================================
# VISUAL SEARCH TASK (like MOT class)
# ======================================================
 
class VisualSearch(GeneralTask):
    def __init__(self, config):
        super().__init__(config)
        pygame.init()
 
        self.config = config
        self.window = pygame.display.set_mode(
            (config["vs"]["width"], config["vs"]["height"])
        )
        self.clock = pygame.time.Clock()
 
        self.stimuli = pygame.sprite.Group()
 
    def _create_stimuli(self):
        self.stimuli.empty()
        vs = self.config["vs"]
 
        num_items = vs["num_items"]
        target_idx = random.randint(0, num_items - 1)
        target_angle = random.choice(vs["angles"])
 
        for i in range(num_items):
            x = random.randint(50, self.window.get_width() - 50)
            y = random.randint(50, self.window.get_height() - 50)
 
            if i == target_idx:
                stim = TStimulus(True, target_angle, None, x, y, vs["stim_size"])
            else:
                stim = TStimulus(False,
                                 random.choice(vs["angles"]),
                                 random.choice(vs["defective_types"]),
                                 x, y, vs["stim_size"])
 
            self.stimuli.add(stim)
 
        self.correct_key = {
            0: pygame.K_UP,
            90: pygame.K_LEFT,
            180: pygame.K_DOWN,
            270: pygame.K_RIGHT,
        }[target_angle]
 
    def single_trial(self):
        vs = self.config["vs"]
        colors = self.config["colors"]
 
        self._create_stimuli()
 
        start = time.time()
        running = True
        responded = False
 
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN and not responded:
                    rt = (time.time() - start) * 1000
                    correct = event.key == self.correct_key
                    return correct, rt
 
            self.window.fill(colors["gray"])
            self.stimuli.draw(self.window)
            pygame.display.flip()
 
            self.clock.tick(60)
 
    def execute(self):
        vs = self.config["vs"]
        results = []
 
        for trial in range(vs["total_trials"]):
            result = self.single_trial()
            results.append(result)
            pygame.time.delay(vs["iti_time"])
 
        return results