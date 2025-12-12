import yaml
from pathlib import Path

# path to config.yaml
CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

with open(CONFIG_PATH, "r") as f:
    _config = yaml.safe_load(f)

# ---- expose values as Python symbols ----
WHITE = tuple(_config["colors"]["white"])
BLACK = tuple(_config["colors"]["black"])
GRAY  = tuple(_config["colors"]["gray"])

WIDTH  = _config["window"]["width"]
HEIGHT = _config["window"]["height"]

TOTAL_TRIALS = _config["experiment"]["total_trials"]
DIFFICULTY_LEVELS = _config["experiment"]["difficulty_levels"]
ITI_TIME = _config["timing"]["iti_time"]

CORRECT_SOUND_FILE = _config["files"]["correct_sound"]
RESULTS_FILE = _config["files"]["results"]

# timing
FIXATION_TIME = _config["timing"]["fixation_time"]
ISI_TIME = _config["timing"]["isi_time"]
RESPONSE_TIMEOUT = _config["timing"]["response_timeout"]
ITI_TIME = _config["timing"]["iti_time"]

# stimuli / geometry
ANGLES = _config["stimuli"]["angles"]
DEFECTIVE_TYPES = _config["stimuli"]["defective_types"]
STIM_SIZE = _config["stimuli"]["stim_size"]
