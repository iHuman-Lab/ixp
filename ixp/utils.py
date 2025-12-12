# utils.py
from contextlib import contextmanager

@contextmanager
def skip_run(mode, name):
    if mode == "run":
        yield lambda: True
    else:
        yield lambda: False
