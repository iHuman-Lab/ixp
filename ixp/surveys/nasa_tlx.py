from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from psychopy import core, event, visual

from ixp.task import Task

from .utils import build_ui

QUESTIONS = [
    ('Mental Demand', 'How mentally demanding was the task?', 'Very Low', 'Very High'),
    ('Physical Demand', 'How physically demanding was the task?', 'Very Low', 'Very High'),
    ('Temporal Demand', 'How hurried or rushed was the pace of the task?', 'Very Low', 'Very High'),
    ('Performance', 'How successful were you in accomplishing what you were asked to do?', 'Perfect', 'Failure'),
    ('Effort', 'How hard did you have to work to accomplish your level of performance?', 'Very Low', 'Very High'),
    ('Frustration', 'How insecure, discouraged, irritated, stressed, and annoyed were you?', 'Very Low', 'Very High'),
]


class NasaTLX(Task):
    def __init__(self, config: dict | None = None):
        self.cfg = config or {}

    def show_all_questions(self, win) -> dict[str, int]:
        texts, sliders, instruction = build_ui(win, QUESTIONS)

        while True:
            for t in texts:
                t.draw()
            for s in sliders:
                s.draw()
            instruction.draw()
            win.flip()

            keys = event.getKeys(['space', 'escape'])
            if 'escape' in keys:
                win.close()
                core.quit()
            if 'space' in keys:
                # Check if all sliders have been touched/rated
                return {f'Q{idx + 1}_{QUESTIONS[idx][0]}': s.markerPos for idx, s in enumerate(sliders)}

    def execute(self) -> dict[str, Any]:
        win = visual.Window(
            size=self.cfg.get('size', [1100, 800]),
            fullscr=self.cfg.get('fullscreen', False),
            color=[-0.6, -0.6, -0.6],  # Slightly lighter grey for contrast
            units='height',  # This is key for proportional scaling
        )

        ratings = self.show_all_questions(win)

        results = {'Timestamp': datetime.now(tz=timezone.utc).isoformat(timespec='seconds')}
        results.update(ratings)

        # Save CSV
        output_file = self.cfg.get('nasa_tlx_save_path', 'nasa_tlx_results.csv')
        with Path(output_file).open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=results.keys())
            writer.writeheader()
            writer.writerow(results)

        win.close()
        return results
