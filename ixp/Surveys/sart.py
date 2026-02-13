from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Any, Dict, List

import pygame

from ixp.individual_difference.utils import check_quit, create_window, show_fixation
from ixp.task import GeneralTask

QUESTIONS = [
    ('Instability of Situation', 'How changeable is the situation? Is the situation highly unstable and likely to change suddenly (High), or is it very stable and straightforward (Low)?'),
    ('Complexity of Situation', 'How complicated is the situation? Is it complex with many interrelated components (High), or is it simple and straightforward (Low)?'),
    ('Variability of Situation', 'How many variables are changing within the situation? Are there a large number of factors varying (High), or are there very few variables changing (Low)?'),
    ('Arousal', 'How aroused are you in the situation? Are you alert and ready for activity (High), or do you have a low degree of alertness (Low)?'),
    ('Concentration of Attention', 'How much are you concentrating on the situation? Are you concentrating on many aspects of the situation (High), or focused on only one (Low)?'),
    ('Division of Attention', 'How much is your attention divided in the situation? Are you concentrating on many aspects of the situation (High), or focused on only one (Low)?'),
    ('Spare Mental Capacity', 'How much mental capacity do you have to spare in the situation? Do you have sufficient capacity to attend to many variables (High), or nothing to spare at all (Low)?'),
    ('Information Quantity', 'How much information have you gained about the situation? Have you received and understood a great deal of knowledge (High), or very little (Low)?'),
    ('Familiarity with Situation', 'How familiar are you with the situation? Do you have a great deal of relevant experience (High), or is it a new situation (Low)?'),
]


class SART(GeneralTask):
    """SART-like questionnaire (7-point Likert) implemented with pygame."""

    def __init__(self, config: dict | None = None):
        super().__init__(config or {})
        self.cfg = config or {}
        self.window_cfg = self.cfg.get('window', {'width': 1100, 'height': 800, 'fullscreen': False})

    def _collect_info(self) -> Dict[str, str]:
        try:
            name = input('Participant Name (optional): ').strip()
        except EOFError:
            name = ''
        try:
            task = input('Task name (optional): ').strip()
        except EOFError:
            task = ''
        return {'Name': name, 'Task': task, 'Date': datetime.now().strftime('%Y-%m-%d')}

    def execute(self) -> Dict[str, Any] | None:
        info = self.cfg.get('info') or self._collect_info()
        window = create_window(self.window_cfg)

        font = pygame.font.Font(None, 40)
        title = font.render('SART - 7-point Likert questionnaire', True, (255, 255, 255))
        window.fill((0, 0, 0))
        window.blit(title, title.get_rect(center=(window.get_width() // 2, 80)))
        hint = font.render('Rate each item (1..7). Use ←/→ or click. Press SPACE to confirm.', True, (255, 255, 255))
        window.blit(hint, hint.get_rect(center=(window.get_width() // 2, 150)))
        pygame.display.flip()

        waiting = True
        while waiting:
            for ev in pygame.event.get():
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_ESCAPE):
                    waiting = False
                if check_quit([ev]):
                    pygame.quit()
                    return None

        show_fixation(window, (120, 120, 120), (255, 255, 255), 500)

        results: Dict[str, Any] = {'Name': info.get('Name', ''), 'Task': info.get('Task', ''), 'Date': info.get('Date', '')}
        results['Timestamp'] = datetime.now().isoformat(timespec='seconds')

        font_small = pygame.font.Font(None, 28)
        large_font = pygame.font.Font(None, 56)

        for idx, (label, question) in enumerate(QUESTIONS, start=1):
            value = 4  # middle of 1..7
            clock = pygame.time.Clock()
            confirmed = False
            while not confirmed:
                events = pygame.event.get()
                if check_quit(events):
                    pygame.quit()
                    raise SystemExit

                for ev in events:
                    if ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_LEFT:
                            value = max(1, value - 1)
                        elif ev.key == pygame.K_RIGHT:
                            value = min(7, value + 1)
                        elif ev.key == pygame.K_SPACE:
                            results[f'Q{idx}_{label}'] = int(value)
                            confirmed = True
                    elif ev.type == pygame.MOUSEBUTTONDOWN:
                        mx, my = ev.pos
                        rail_rect = pygame.Rect(int(window.get_width() * 0.15), int(window.get_height() * 0.5), int(window.get_width() * 0.7), 28)
                        if rail_rect.collidepoint(mx, my):
                            rel = mx - rail_rect.left
                            proportion = rel / rail_rect.width
                            # map proportion to 1..7
                            value = int(round(1 + proportion * 6))

                # render
                window.fill((30, 30, 30))
                header = large_font.render(f'{idx}. {label}', True, (255, 255, 255))
                window.blit(header, (40, 40))

                wrapped = _wrap_text(question, font_small, window.get_width() - 80)
                _draw_text_lines(window, font_small, wrapped, (255, 255, 255), 40, 120)

                # draw rail
                rail_rect = pygame.Rect(int(window.get_width() * 0.15), int(window.get_height() * 0.5), int(window.get_width() * 0.7), 28)
                _draw_slider(window, rail_rect, (value - 1) / 6.0 * 100.0, (200, 200, 200), (250, 250, 250))

                # numeric labels 1..7
                for n in range(1, 8):
                    tx = rail_rect.left + int(((n - 1) / 6.0) * rail_rect.width)
                    num_surf = font_small.render(str(n), True, (255, 255, 255))
                    num_x = tx - num_surf.get_width() // 2
                    num_y = rail_rect.bottom + 18
                    window.blit(num_surf, (num_x, num_y))

                hint2 = font_small.render('Use ←/→ or click; SPACE to confirm.', True, (200, 200, 200))
                window.blit(hint2, (40, window.get_height() - 60))

                pygame.display.flip()
                clock.tick(30)

        # write CSV
        fieldnames = list(results.keys())
        file_exists = os.path.exists(self.cfg.get('output_file', 'sart_results.csv'))
        with open(self.cfg.get('output_file', 'sart_results.csv'), 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(results)

        # done
        done_font = pygame.font.Font(None, 64)
        done = done_font.render('Done ✅ Thank you!', True, (255, 255, 255))
        window.fill((0, 0, 0))
        window.blit(done, done.get_rect(center=(window.get_width() // 2, window.get_height() // 2)))
        pygame.display.flip()
        pygame.time.wait(1200)
        pygame.quit()
        return results


# helpers reused from nasa_tlx_pygame

def _draw_text_lines(window, font, lines: List[str], color, x: int, y: int, line_spacing: int = 6):
    for line in lines:
        surf = font.render(line, True, color)
        window.blit(surf, (x, y))
        y += surf.get_height() + line_spacing


def _wrap_text(text: str, font, max_width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    cur = ''
    for w in words:
        test = (cur + ' ' + w).strip()
        if font.size(test)[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _draw_slider(window, rect, value: float, rail_color, knob_color):
    # rail
    pygame.draw.rect(window, rail_color, rect)
    # knob position
    x = rect.left + int((value / 100.0) * rect.width)
    knob_rect = pygame.Rect(0, 0, 12, rect.height + 10)
    knob_rect.center = (x, rect.centery)
    pygame.draw.rect(window, knob_color, knob_rect)


def run_survey(info: Dict[str, Any] | None = None, out_csv: str = 'sart_results.csv'):
    cfg = {'info': info or None, 'output_file': out_csv}
    task = SART(cfg)
    return task.execute()


__all__ = ['run_survey']
