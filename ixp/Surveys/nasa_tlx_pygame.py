from __future__ import annotations

from datetime import datetime
import csv
import os
from typing import Dict, Any, List

import pygame

from ixp.individual_difference.utils import create_window, show_fixation, check_quit
from ixp.task import GeneralTask


class NASA_TLX(GeneralTask):
    """NASA-TLX questionnaire implemented with pygame in a class matching MOT/VS style."""

    def __init__(self, config: dict | None = None):
        super().__init__(config or {})
        self.cfg = config or {}
        # window config fallback
        self.window_cfg = self.cfg.get("window", {"width": 1100, "height": 800, "fullscreen": False})

    def _collect_info(self) -> Dict[str, str]:
        # basic participant info via console fallback; kept simple
        try:
            name = input("Participant Name (optional): ").strip()
        except EOFError:
            name = ""
        try:
            task = input("Task name (optional): ").strip()
        except EOFError:
            task = ""
        return {"Name": name, "Task": task, "Date": datetime.now().strftime("%Y-%m-%d")}

    def execute(self) -> Dict[str, Any] | None:
        info = self.cfg.get("info") or self._collect_info()

        window = create_window(self.window_cfg)

        # title screen
        font = pygame.font.Font(None, 48)
        msg = font.render("NASA-TLX - Rate each scale, then press SPACE. (ESC to quit)", True, (255, 255, 255))
        window.fill((0, 0, 0))
        window.blit(msg, msg.get_rect(center=(window.get_width() // 2, window.get_height() // 2)))
        pygame.display.flip()
        # wait for confirmation
        waiting = True
        while waiting:
            for ev in pygame.event.get():
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_ESCAPE):
                    waiting = False
                if check_quit([ev]):
                    pygame.quit()
                    return None

        # short fixation
        show_fixation(window, (120, 120, 120), (255, 255, 255), 500)

        results = run_tlx(window, info, out_csv=self.cfg.get("output_file", "nasa_tlx_results.csv"), step=self.cfg.get("step", 5))

        # done
        done_font = pygame.font.Font(None, 64)
        done = done_font.render("Done ✅ Thank you!", True, (255, 255, 255))
        window.fill((0, 0, 0))
        window.blit(done, done.get_rect(center=(window.get_width() // 2, window.get_height() // 2)))
        pygame.display.flip()
        pygame.time.wait(1200)
        pygame.quit()
        return results


def _draw_text_lines(window, font, lines: List[str], color, x: int, y: int, line_spacing: int = 6):
    for line in lines:
        surf = font.render(line, True, color)
        window.blit(surf, (x, y))
        y += surf.get_height() + line_spacing


def _wrap_text(text: str, font, max_width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
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


def run_tlx(window, info: Dict[str, Any], out_csv: str = "nasa_tlx_results.csv", step: int = 5):
    items = [
        ("MentalDemand", "Mental Demand", "How mentally demanding was the task?", "Very Low", "Very High"),
        ("PhysicalDemand", "Physical Demand", "How physically demanding was the task?", "Very Low", "Very High"),
        ("TemporalDemand", "Temporal Demand", "How hurried or rushed was the pace of the task?", "Very Low", "Very High"),
        ("Performance", "Performance", "How successful were you in accomplishing what you were asked to do?", "Perfect", "Failure"),
        ("Effort", "Effort", "How hard did you have to work to accomplish your level of performance?", "Very Low", "Very High"),
        ("Frustration", "Frustration", "How insecure, discouraged, irritated, stressed, and annoyed were you?", "Very Low", "Very High"),
    ]

    bg = (120, 120, 120)
    text_color = (255, 255, 255)
    rail_color = (200, 200, 200)
    knob_color = (250, 250, 250)

    font = pygame.font.Font(None, 28)
    large_font = pygame.font.Font(None, 72)

    results: Dict[str, Any] = {"Name": info.get("Name", ""), "Task": info.get("Task", ""), "Date": info.get("Date", "")}
    results["Timestamp"] = datetime.now().isoformat(timespec="seconds")

    for key, title, question, left_label, right_label in items:
        # slider state
        value = 50.0

        clock = pygame.time.Clock()
        while True:
            events = pygame.event.get()
            if check_quit(events):
                raise SystemExit

            for ev in events:
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_LEFT:
                        value = max(0, value - step)
                    elif ev.key == pygame.K_RIGHT:
                        value = min(100, value + step)
                    elif ev.key == pygame.K_SPACE:
                        # confirm
                        results[key] = float(value)
                        break
                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = ev.pos
                    # compute if click on rail
                    rail_rect = pygame.Rect(window.get_width() * 0.1, window.get_height() * 0.5, int(window.get_width() * 0.8), 24)
                    if rail_rect.collidepoint(mx, my):
                        rel = mx - rail_rect.left
                        value = (rel / rail_rect.width) * 100.0

            # render
            window.fill(bg)
            header = large_font.render(title, True, text_color)
            window.blit(header, header.get_rect(center=(window.get_width() // 2, 80)))

            wrapped = _wrap_text(question, font, window.get_width() - 80)
            _draw_text_lines(window, font, wrapped, text_color, 40, 160)

            # labels
            left_surf = font.render(left_label, True, text_color)
            right_surf = font.render(right_label, True, text_color)
            # rail
            rail_rect = pygame.Rect(int(window.get_width() * 0.1), int(window.get_height() * 0.5), int(window.get_width() * 0.8), 24)
            _draw_slider(window, rail_rect, value, rail_color, knob_color)
            window.blit(left_surf, (rail_rect.left, rail_rect.bottom + 8))
            window.blit(right_surf, (rail_rect.right - right_surf.get_width(), rail_rect.bottom + 8))

            # numeric tick labels at 0,10,...,100
            for n in range(0, 101, 10):
                tx = rail_rect.left + int((n / 100.0) * rail_rect.width)
                num_surf = font.render(str(n), True, text_color)
                num_x = tx - num_surf.get_width() // 2
                num_y = rail_rect.bottom + 28
                window.blit(num_surf, (num_x, num_y))

            hint = font.render("Click the line or use ←/→. Press SPACE to confirm.", True, text_color)
            window.blit(hint, (40, window.get_height() - 60))

            pygame.display.flip()
            clock.tick(30)
            # if confirmed, break outer loop
            if key in results:
                break

    # write CSV
    fieldnames = list(results.keys())
    file_exists = os.path.exists(out_csv)

    with open(out_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(results)

    return results


def run_survey(info: Dict[str, Any] | None = None, out_csv: str = "nasa_tlx_results.csv", step: int = 5):
    cfg = {"info": info or None, "output_file": out_csv, "step": step}
    task = NASA_TLX(cfg)
    return task.execute()


__all__ = ["run_survey"]
