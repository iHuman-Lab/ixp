from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

from ixp.task import GeneralTask
from ixp.individual_difference.utils import create_window, parse_color, check_quit, show_fixation



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


def _load_survey_config() -> Dict[str, Any]:
    try:
        base = Path(__file__).resolve().parents[2]
        cfg_path = base / "configs" / "config.yaml"
        if cfg_path.exists():
            with cfg_path.open("r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            return cfg.get("survey") or {}
    except Exception:
        traceback.print_exc()
    return {}


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
            # Prefer pygame UI if configured and available
            survey_cfg = _load_survey_config()
            use_pygame = bool(survey_cfg.get("use_pygame", True))

            if use_pygame:
                try:
                    return self._run_pygame(survey_cfg)
                except Exception:
                    # Fall back to console if pygame UI fails
                    traceback.print_exc()
                    print("Pygame UI failed; falling back to console.")

            # Console fallback
            print("\n--- NASA-TLX Brief Questionnaire (console) ---\n")

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

    def _run_pygame(self, survey_cfg: Dict[str, Any]) -> Dict[str, Any]:
        # Window config
        window_cfg = survey_cfg.get("window") or {"width": 800, "height": 600, "fullscreen": False}
        # merge background/text color
        bg = tuple(survey_cfg.get("background_color", [120, 120, 120]))
        text_color = tuple(survey_cfg.get("text_color", [0, 0, 0]))

        window = create_window(window_cfg)
        pygame_font = None
        try:
            import pygame

            pygame.display.set_caption("NASA-TLX Questionnaire")
            pygame_font = pygame.font.Font(None, 28)
        except Exception:
            raise

        # simple fixation before starting
        show_fixation(window, bg, text_color, 500)

        # Participant ID input via pygame
        participant = self._pygame_text_input(window, pygame_font, bg, text_color, "Participant ID (optional): ")
        self.results = {"timestamp": datetime.utcnow().isoformat(), "participant": participant, "answers": {}}

        for q in self.questions:
            qtype = q.get("type")
            if qtype == "scale":
                val = self._pygame_scale_input(window, pygame_font, bg, text_color, q)
                self.results["answers"][q["id"]] = val
            elif qtype == "text":
                txt = self._pygame_text_input(window, pygame_font, bg, text_color, q.get("text"))
                self.results["answers"][q["id"]] = txt
            else:
                # fallback to console for unsupported types
                self.results["answers"][q["id"]] = None

        fname = self._save_results()
        return self.results

    def _pygame_scale_input(self, window, font, bg, text_color, question: Dict[str, Any]) -> int:
        import pygame

        min_v = int(question.get("min", 0))
        max_v = int(question.get("max", 20))
        val = (min_v + max_v) // 2
        prompt = question.get("text")

        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if check_quit([event]):
                    raise SystemExit
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        val = max(min_v, val - 1)
                    elif event.key == pygame.K_RIGHT:
                        val = min(max_v, val + 1)
                    elif event.key == pygame.K_RETURN:
                        return val
            window.fill(bg)
            # render prompt
            lines = self._wrap_text(prompt, font, window.get_width() - 40)
            y = 40
            for line in lines:
                txt_surf = font.render(line, True, text_color)
                window.blit(txt_surf, (20, y))
                y += txt_surf.get_height() + 4

            # render current value
            val_surf = font.render(f"Value: {val}  (Use ← → to change, Enter to confirm)", True, text_color)
            window.blit(val_surf, (20, window.get_height() - 60))

            pygame.display.flip()
            clock.tick(30)

    def _pygame_text_input(self, window, font, bg, text_color, prompt: str) -> str:
        import pygame

        text = ""
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if check_quit([event]):
                    raise SystemExit
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        return text.strip()
                    elif event.key == pygame.K_BACKSPACE:
                        text = text[:-1]
                    else:
                        if event.unicode:
                            text += event.unicode
            window.fill(bg)
            lines = self._wrap_text(prompt, font, window.get_width() - 40)
            y = 40
            for line in lines:
                txt_surf = font.render(line, True, text_color)
                window.blit(txt_surf, (20, y))
                y += txt_surf.get_height() + 4

            # render current entry
            entry_surf = font.render(text or "(type and press Enter to confirm)", True, text_color)
            window.blit(entry_surf, (20, window.get_height() - 60))

            pygame.display.flip()
            clock.tick(30)

    def _wrap_text(self, text: str, font, max_width: int) -> List[str]:
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
