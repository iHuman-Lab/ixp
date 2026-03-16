from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from psychopy import core, event, visual

from ixp.task import Task

from .utils import build_ui

# Full SART Questions
QUESTIONS = [
    (
        "Instability",
        "How changeable is the situation? Is it unstable or stable?",
        "Unstable",
        "Stable",
    ),
    (
        "Complexity",
        "How complicated is the situation? Complex or simple?",
        "Complex",
        "Simple",
    ),
    ("Variability", "How many factors are changing? Many or few?", "Many", "Few"),
    ("Arousal", "How alert/ready are you? High alertness or low?", "High", "Low"),
    (
        "Concentration",
        "How much are you concentrating? Many aspects or one?",
        "Many",
        "Few",
    ),
    ("Division", "How divided is your attention?", "High", "Low"),
    (
        "Spare Capacity",
        "How much mental capacity is left? Sufficient or none?",
        "Sufficient",
        "None",
    ),
    (
        "Information",
        "How much info have you gained? Great deal or very little?",
        "High",
        "Low",
    ),
    (
        "Familiarity",
        "How familiar are you with the experience",
        "Familiar",
        "Not Familiar",
    ),
]


class SART(Task):
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

            keys = event.getKeys(["space", "escape"])
            if "escape" in keys:
                win.close()
                core.quit()
            if "space" in keys:
                # Check if all sliders have been touched/rated
                return {
                    f"Q{idx + 1}_{QUESTIONS[idx][0]}": s.markerPos
                    for idx, s in enumerate(sliders)
                }

    def execute(self) -> dict[str, Any]:
        win = visual.Window(
            size=self.cfg.get(
                "size", [1200, 950]
            ),  # Taller window recommended for 9 questions
            fullscr=self.cfg.get("fullscreen", False),
            screen=self.cfg.get("display", 0),
            color=[-0.8, -0.8, -0.8],
            units="height",
            checkTiming=False,
        )

        ratings = self.show_all_questions(win)

        results = {
            "Timestamp": datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
        }
        results.update(ratings)

        win.close()
        return results
