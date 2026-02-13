
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pygame

from ixp.individual_difference.utils import check_quit, create_window, save_results, show_fixation
from ixp.task import GeneralTask

QUESTIONS = [
    ("Mental Demand", "How mentally demanding was the task?", "Very Low", "Very High"),
    ("Physical Demand", "How physically demanding was the task?", "Very Low", "Very High"),
    ("Temporal Demand", "How hurried or rushed was the pace of the task?", "Very Low", "Very High"),
    ("Performance", "How successful were you in accomplishing what you were asked to do?", "Perfect", "Failure"),
    ("Effort", "How hard did you have to work to accomplish your level of performance?", "Very Low", "Very High"),
    ("Frustration", "How insecure, discouraged, irritated, stressed, and annoyed were you?", "Very Low", "Very High"),
]
_WHITE, _BLACK, _DARK = (255, 255, 255), (0, 0, 0), (30, 30, 30)
_GRAY, _HANDLE = (200, 200, 200), (255, 0, 0)
_MIN, _MAX = 1, 100


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _wrap_text(text: str, font: pygame.font.Font, max_w: int) -> list[str]:
    lines, cur = [], ''
    for w in text.split():
        test = f'{cur} {w}'.strip()
        if font.size(test)[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _rail(win: pygame.Surface) -> pygame.Rect:
    w, h = win.get_width(), win.get_height()
    return pygame.Rect(int(w * 0.15), int(h * 0.5), int(w * 0.7), 28)


class SART(GeneralTask):
    """SART-like questionnaire (7-point Likert) with pygame."""

    def __init__(self, config: dict | None = None):
        super().__init__(config or {})
        self.cfg = config or {}

    def _draw_slider(self, win: pygame.Surface, rail: pygame.Rect,
                     value: int, fs: pygame.font.Font) -> None:
        """Draw the rail, tick marks, handle, and anchors."""
        pygame.draw.rect(win, _GRAY, rail, border_radius=6)
        for i in range(21):
            x = rail.left + int(i / 20 * rail.width)
            h = 16 if i % 5 == 0 else 8
            pygame.draw.line(win, _WHITE, (x, rail.top - h), (x, rail.top), 2)
        hx = rail.left + int((value - _MIN) / (_MAX - _MIN) * rail.width)
        pygame.draw.circle(win, _HANDLE, (_clamp(hx, rail.left, rail.right - 1), rail.centery), 14)
        win.blit(fs.render('Low', True, _WHITE), (rail.left, rail.bottom + 18))
        hi = fs.render('High', True, _WHITE)
        win.blit(hi, (rail.right - hi.get_width(), rail.bottom + 18))

    def _ask_question(self, win: pygame.Surface, idx: int, label: str,
                      question: str, fs: pygame.font.Font, fb: pygame.font.Font) -> int:
        value, rail, clock = 50, _rail(win), pygame.time.Clock()
        wrapped = _wrap_text(question, fs, win.get_width() - 80)

        while True:
            for ev in pygame.event.get():
                if check_quit([ev]):
                    pygame.quit()
                    raise SystemExit
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_LEFT:
                        value = _clamp(value - 5, _MIN, _MAX)
                    elif ev.key == pygame.K_RIGHT:
                        value = _clamp(value + 5, _MIN, _MAX)
                    elif ev.key == pygame.K_SPACE:
                        return value
                elif ev.type == pygame.MOUSEBUTTONDOWN and rail.collidepoint(ev.pos):
                    value = _clamp(int(round(_MIN + (ev.pos[0] - rail.left) / rail.width * (_MAX - _MIN))), _MIN, _MAX)

            win.fill(_DARK)
            win.blit(fb.render(f'{idx}. {label}', True, _WHITE), (40, 40))
            y = 120
            for line in wrapped:
                win.blit(fs.render(line, True, _WHITE), (40, y))
                y += fs.get_linesize()
            self._draw_slider(win, rail, value, fs)
            win.blit(fs.render('\u2190/\u2192 or click; SPACE to confirm', True, _GRAY), (40, win.get_height() - 60))
            pygame.display.flip()
            clock.tick(30)

    def execute(self) -> dict[str, Any] | None:
        win = create_window(self.cfg.get('window', {'width': 1100, 'height': 800, 'fullscreen': False}))
        show_fixation(win, (120, 120, 120), _WHITE, 500)

        results: dict[str, Any] = {
            'Timestamp': datetime.now(tz=timezone.utc).isoformat(timespec='seconds'),
        }
        fs, fb = pygame.font.Font(None, 28), pygame.font.Font(None, 56)
        for idx, (label, question) in enumerate(QUESTIONS, start=1):
            results[f'Q{idx}_{label}'] = self._ask_question(win, idx, label, question, fs, fb)

        save_results(self.cfg.get('output_file', 'nasa_tlx_results.csv'),
                     list(results.keys()), [list(results.values())])
        pygame.quit()
        return results

