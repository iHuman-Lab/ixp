from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

from ixp.task import GeneralTask

SURVEYS_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SURVEYS_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)


DEFAULT_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "tlx_mental_demand",
        "text": "Mental Demand — How mentally demanding was the task?",
        "type": "scale",
        "min": 0,
        "max": 20,
        "left_label": "Very Low",
        "right_label": "Very High",
    },
    {
        "id": "tlx_physical_demand",
        "text": "Physical Demand — How physically demanding was the task?",
        "type": "scale",
        "min": 0,
        "max": 20,
        "left_label": "Very Low",
        "right_label": "Very High",
    },
    {
        "id": "tlx_temporal_demand",
        "text": "Temporal Demand — How hurried or rushed was the pace of the task?",
        "type": "scale",
        "min": 0,
        "max": 20,
        "left_label": "Very Low",
        "right_label": "Very High",
    },
    {
        "id": "tlx_performance",
        "text": "Performance — How successful were you in accomplishing what you were asked to do?",
        "type": "scale",
        "min": 0,
        "max": 20,
        "left_label": "Perfect",
        "right_label": "Failure",
    },
    {
        "id": "tlx_effort",
        "text": "Effort — How hard did you have to work to accomplish your level of performance?",
        "type": "scale",
        "min": 0,
        "max": 20,
        "left_label": "Very Low",
        "right_label": "Very High",
    },
    {
        "id": "tlx_frustration",
        "text": "Frustration — How insecure, discouraged, irritated, stressed, and annoyed were you?",
        "type": "scale",
        "min": 0,
        "max": 20,
        "left_label": "Very Low",
        "right_label": "Very High",
    },
    {
        "id": "comments",
        "text": "Any additional comments? (press Enter to skip)",
        "type": "text",
    },
]


def _load_questions_from_config() -> List[Dict[str, Any]]:
    try:
        base = Path(__file__).resolve().parents[2]
        cfg_path = base / "configs" / "config.yaml"
        if cfg_path.exists():
            with cfg_path.open("r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            survey = cfg.get("survey") or {}
            qs = survey.get("questions")
            if isinstance(qs, list) and qs:
                return qs
    except Exception:
        traceback.print_exc()
    return DEFAULT_QUESTIONS


def _ask_single_question(question: Dict[str, Any]) -> Any:
    print(question["text"])
    opts = question.get("options") or []
    if opts:
        for i, opt in enumerate(opts, start=1):
            print(f"  {i}. {opt}")
        while True:
            choice = input("Select option number: ").strip()
            if not choice:
                print("Please enter a selection.")
                continue
            if not choice.isdigit():
                print("Please enter a valid number.")
                continue
            idx = int(choice)
            if 1 <= idx <= len(opts):
                return opts[idx - 1]
            print("Choice out of range. Try again.")
    else:
        return input().strip()


def _ask_scale_question(question: Dict[str, Any]) -> int:
    min_v = int(question.get("min", 0))
    max_v = int(question.get("max", 20))
    left = question.get("left_label", "")
    right = question.get("right_label", "")
    prompt = f"{question.get('text')}\nEnter a value between {min_v} ({left}) and {max_v} ({right}): "
    while True:
        val = input(prompt).strip()
        if val == "":
            print("Please enter a value.")
            continue
        try:
            ival = int(val)
        except ValueError:
            print("Please enter an integer value.")
            continue
        if ival < min_v or ival > max_v:
            print(f"Value out of range ({min_v}-{max_v}). Try again.")
            continue
        return ival


class Questionnaire(GeneralTask):
    """Simple console questionnaire task (TLX-style) that follows the
    `GeneralTask` structure used by MOT/VS.

    This class does not depend on pygame and is intended to be executed in
    the main process so it can access stdin. Use the `run_survey()` helper
    to call it from `main.py` after Ray is shut down.
    """

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config or {})
        self.cfg = config or {}
        self.questions = self.cfg.get("questions") or _load_questions_from_config()
        self.results: Dict[str, Any] = {"timestamp": None, "participant": None, "answers": {}}

    def execute(self) -> Dict[str, Any]:
        return self.run()

    def run(self) -> Dict[str, Any]:
        try:
            print("\n--- NASA-TLX Brief Questionnaire ---\n")

            if not sys.stdin or not sys.stdin.isatty():
                print("Non-interactive environment detected: saving placeholder survey result.")
                self.results = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "participant": None,
                    "answers": {q["id"]: None for q in self.questions},
                    "non_interactive": True,
                }
                fname = self._save_results(non_interactive=True)
                print(f"Survey saved to: {fname}")
                return self.results

            participant = input("Participant ID (optional): ").strip()
            self.results = {"timestamp": datetime.utcnow().isoformat(), "participant": participant, "answers": {}}

            for q in self.questions:
                qtype = q.get("type")
                if qtype == "single":
                    ans = _ask_single_question(q)
                elif qtype == "text":
                    print(q["text"])
                    ans = input().strip()
                elif qtype == "scale":
                    ans = _ask_scale_question(q)
                else:
                    ans = None
                self.results["answers"][q["id"]] = ans
                print()

            fname = self._save_results()
            print(f"Survey saved to: {fname}")
            return self.results
        except Exception:
            print("Survey encountered an error; saving placeholder result.", file=sys.stderr)
            traceback.print_exc()
            self.results = {
                "timestamp": datetime.utcnow().isoformat(),
                "participant": None,
                "answers": {q.get("id", f"q{i}"): None for i, q in enumerate(self.questions or DEFAULT_QUESTIONS, start=1)},
                "error": True,
            }
            fname = self._save_results(error=True)
            print(f"Survey saved to: {fname}")
            return self.results

    def _save_results(self, non_interactive: bool = False, error: bool = False) -> Path:
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        suffix = ""
        if non_interactive:
            suffix = "_noninteractive"
        if error:
            suffix = "_error"
        fname = RESULTS_DIR / f"survey_{ts}{suffix}.json"
        with fname.open("w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        return fname


def run_survey(questions: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    cfg = {"questions": questions} if questions is not None else None
    q = Questionnaire(cfg)
    return q.run()
