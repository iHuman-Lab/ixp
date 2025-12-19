import yaml
from pathlib import Path

# -------------------------------------------------
# LOAD CONFIG
# -------------------------------------------------
CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

with open(CONFIG_PATH, "r") as f:
    _config = yaml.safe_load(f)

# -------------------------------------------------
# COLORS
# -------------------------------------------------
WHITE = tuple(_config["colors"]["white"])
BLACK = tuple(_config["colors"]["black"])
GRAY  = tuple(_config["colors"]["gray"])

# -------------------------------------------------
# WINDOW
# -------------------------------------------------
WIDTH  = _config["window"]["width"]
HEIGHT = _config["window"]["height"]

# -------------------------------------------------
# VISUAL SEARCH (FIXED DIFFICULTY)
# -------------------------------------------------
TOTAL_TRIALS = _config["vs"]["total_trials"]
NUM_ITEMS    = _config["vs"]["num_items"]
ITI_TIME     = _config["vs"]["iti_time"]

# -------------------------------------------------
# TIMING
# -------------------------------------------------
FIXATION_TIME     = _config["timing"]["fixation_time"]
ISI_TIME          = _config["timing"]["isi_time"]
RESPONSE_TIMEOUT  = _config["timing"]["response_timeout"]

# -------------------------------------------------
# STIMULI
# -------------------------------------------------
ANGLES           = _config["stimuli"]["angles"]
DEFECTIVE_TYPES  = _config["stimuli"]["defective_types"]
STIM_SIZE        = _config["stimuli"]["stim_size"]

# -------------------------------------------------
# FILES
# -------------------------------------------------
RESULTS_FILE = _config["files"]["results"]
