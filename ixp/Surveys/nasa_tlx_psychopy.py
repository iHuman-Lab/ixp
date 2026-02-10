from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import csv
import os
from typing import Dict, Any, List, Optional

from ixp.task import GeneralTask


# -----------------------------
# Config
# -----------------------------
@dataclass
class TLXConfig:
    width: int = 1100
    height: int = 800
    fullscreen: bool = False
    screen: int = -1  # -1 = primary
    bg_color: List[float] = (-0.1, -0.1, -0.1)  # PsychoPy uses -1..+1
    output_file: str = "nasa_tlx_results.csv"
    step: int = 5  # slider granularity (0..100)
    font: str = "Arial"


TLX_ITEMS = [
    ("MentalDemand",   "Mental Demand",   "How mentally demanding was the task?",                           "Very Low", "Very High"),
    ("PhysicalDemand", "Physical Demand", "How physically demanding was the task?",                         "Very Low", "Very High"),
    ("TemporalDemand", "Temporal Demand", "How hurried or rushed was the pace of the task?",                "Very Low", "Very High"),
    ("Performance",    "Performance",     "How successful were you in accomplishing what you were asked?",  "Perfect",  "Failure"),
    ("Effort",         "Effort",          "How hard did you have to work to accomplish your performance?",  "Very Low", "Very High"),
    ("Frustration",    "Frustration",     "How insecure, discouraged, irritated, stressed, annoyed were you?", "Very Low", "Very High"),
]


def _collect_info_dialog(title: str = "NASA-TLX Info") -> Optional[Dict[str, str]]:
    info = {
        "Name": "",
        "Task": "",
        "Date": datetime.now().strftime("%Y-%m-%d"),
    }
    from psychopy import gui

    dlg = gui.DlgFromDict(dictionary=info, title=title, fixed=["Date"])
    if not dlg.OK:
        return None
    return info


def _ensure_csv_header(path: str, fieldnames: List[str]) -> None:
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()


def _append_csv_row(path: str, fieldnames: List[str], row: Dict[str, Any]) -> None:
    _ensure_csv_header(path, fieldnames)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(row)


def run_nasa_tlx_psychopy(cfg: TLXConfig, info: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    # Lazy-import PsychoPy here to avoid importing Qt during module import.
    from psychopy import visual, event, core, gui

    def _show_message(win: visual.Window, text: str, cfg: TLXConfig) -> str:
        msg = visual.TextStim(
            win,
            text=text,
            color="white",
            height=0.05,
            wrapWidth=1.4,
            font=cfg.font,
        )
        while True:
            msg.draw()
            win.flip()
            keys = event.getKeys(keyList=["space", "escape"])
            if "escape" in keys:
                return "cancel"
            if "space" in keys:
                return "ok"

    def _fixation(win: visual.Window, secs: float = 0.5) -> None:
        fix = visual.TextStim(win, text="+", color="white", height=0.12)
        fix.draw()
        win.flip()
        core.wait(secs)

    # Participant dialog
    if info is None:
        info = _collect_info_dialog()
        if info is None:
            return None

    # Window
    win = visual.Window(
        size=(cfg.width, cfg.height),
        fullscr=cfg.fullscreen,
        screen=cfg.screen,
        units="norm",
        color=cfg.bg_color,
    )

    try:
        status = _show_message(
            win,
            "NASA-TLX\n\nRate each scale.\n\n- Use mouse to click/drag\n- Or use LEFT/RIGHT arrows\n\nPress SPACE to start.\nPress ESC to quit.",
            cfg,
        )
        if status == "cancel":
            return None

        _fixation(win, secs=0.5)

        results: Dict[str, Any] = {
            "Name": info.get("Name", ""),
            "Task": info.get("Task", ""),
            "Date": info.get("Date", ""),
            "Timestamp": datetime.now().isoformat(timespec="seconds"),
        }

        # Common stimuli
        title_stim = visual.TextStim(win, text="", color="white", height=0.10, pos=(0, 0.75), font=cfg.font)
        q_stim = visual.TextStim(win, text="", color="white", height=0.05, pos=(0, 0.35), wrapWidth=1.6, font=cfg.font)
        hint_stim = visual.TextStim(win, text="Press SPACE to confirm this item (ESC to quit).", color="white",
                                    height=0.04, pos=(0, -0.85), font=cfg.font)

        # Slider: 0..100 with cfg.step increments. Show numeric labels at 0,10,20,...100
        ticks = list(range(0, 101, cfg.step))
        labels = [str(t) if (t % 10 == 0) else "" for t in ticks]
        slider = visual.Slider(
            win,
            ticks=ticks,
            labels=labels,
            pos=(0, -0.10),
            size=(1.5, 0.12),
            granularity=cfg.step,
            style=["rating"],
            color="white",
            markerColor="white",
        )

        left_label = visual.TextStim(win, text="", color="white", height=0.045, pos=(-0.75, -0.25), alignText="left", font=cfg.font)
        right_label = visual.TextStim(win, text="", color="white", height=0.045, pos=(0.75, -0.25), alignText="right", font=cfg.font)

        # Loop items
        for key, title, question, left, right in TLX_ITEMS:
            # reset slider each page
            slider.reset()
            slider.markerPos = 50  # start at mid

            title_stim.text = title
            q_stim.text = question
            left_label.text = left
            right_label.text = right

            while True:
                # quit
                if event.getKeys(keyList=["escape"]):
                    return None

                # keyboard adjustment (optional; mouse already works)
                keys = event.getKeys(keyList=["left", "right", "space"])
                if "left" in keys:
                    slider.markerPos = max(0, slider.markerPos - cfg.step)
                if "right" in keys:
                    slider.markerPos = min(100, slider.markerPos + cfg.step)

                # draw
                title_stim.draw()
                q_stim.draw()
                left_label.draw()
                right_label.draw()
                slider.draw()
                hint_stim.draw()
                win.flip()

                # confirm
                if "space" in keys:
                    # if user never clicked, markerPos still exists (we use that)
                    value = float(slider.markerPos if slider.markerPos is not None else 50.0)
                    results[key] = value
                    break

        # Save CSV
        fieldnames = list(results.keys())
        _append_csv_row(cfg.output_file, fieldnames, results)

        # Done screen
        done = visual.TextStim(win, text="Done ✅\nThank you!", color="white", height=0.10, font=cfg.font)
        done.draw()
        win.flip()
        core.wait(1.2)

        return results

    finally:
        win.close()
        core.quit()


class NASA_TLX(GeneralTask):
    """NASA-TLX implemented as a task class that can be instantiated and executed from main."""

    def __init__(self, config: dict | None = None):
        super().__init__(config or {})
        self.cfg = config or {}

    def execute(self) -> Optional[Dict[str, Any]]:
        cfg = TLXConfig(
            width=self.cfg.get("width", TLXConfig.width),
            height=self.cfg.get("height", TLXConfig.height),
            fullscreen=self.cfg.get("fullscreen", TLXConfig.fullscreen),
            screen=self.cfg.get("screen", TLXConfig.screen),
            bg_color=self.cfg.get("bg_color", TLXConfig.bg_color),
            output_file=self.cfg.get("output_file", TLXConfig.output_file),
            step=self.cfg.get("step", TLXConfig.step),
            font=self.cfg.get("font", TLXConfig.font),
        )
        info = self.cfg.get("info")
        return run_nasa_tlx_psychopy(cfg, info=info)


__all__ = ["run_nasa_tlx_psychopy", "TLXConfig", "NASA_TLX"]
