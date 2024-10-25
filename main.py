from __future__ import annotations

from pathlib import Path

import yaml

from utils import skip_run

# The configuration file
config_path = 'configs/config.yml'
with Path('configs/config.yml').open() as f:
    config = yaml.load(f, Loader=yaml.SafeLoader)

with skip_run('skip', 'test_features') as check, check():
    pass
