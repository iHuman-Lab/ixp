# ixp

> *"Because running experiments shouldn't feel like one."*

A Python package for running behavioral experiments at iHuman Lab.

## What's This All About?

Ever wanted to track eyeballs, chase moving dots, and stream data—all at the same time? Welcome to `ixp`, your new best friend for behavioral experiments.

### The Good Stuff

- **Parallel Processing with Ray** — Run tasks and record sensors simultaneously. Your CPU cores were getting bored anyway.
- **LSL Streaming** — Sync your data across devices like a well-conducted orchestra (via [Lab Streaming Layer](https://labstreaminglayer.org/)).
- **Plug-and-Play Sensors** — Eye trackers, physiological sensors, you name it. If it has data, we can stream it.
- **Flexible Task Design** — Blocks, trials, randomization—structure your experiments however your research heart desires.

### Built-In Cognitive Tasks

Why build from scratch when we've got classics?

| Task                               | What It Does                                                                   |
| ---------------------------------- | ------------------------------------------------------------------------------ |
| **MOT** (Multiple Object Tracking) | "Keep your eyes on the ball"—except there are 8 of them and they're all moving |
| **VS** (Visual Search)             | Find the T among the Ls. Sounds easy until it isn't                            |

## Getting Started

### Installation

**From GitHub (pip):**

```shell
pip install git+https://github.com/ihuman-lab/ixp.git
```

**For development (Poetry):**

```shell
git clone https://github.com/ihuman-lab/ixp.git
cd ixp
poetry install
```

That's it. You're ready to science.

### Adding Dependencies

Need more packages? We got you:

```shell
poetry add <dependency>
```

### Pre-Commit Hooks (For the Tidy Ones)

We use [pre-commit](https://pre-commit.com/) to keep our code clean. Set it up once and forget about it:

```shell
poetry run pre-commit install
```

Want to run it manually? Go wild:

```shell
poetry run pre-commit run --all-files
```

### Testing

We test our code because we're responsible adults (sometimes). Using [pytest](https://docs.pytest.org/en/stable/):

```shell
poetry run pytest
```

Need more details? Crank up the logging:

```shell
poetry run pytest --log-cli-level=DEBUG
```

Check `pyproject.toml` for all the pytest settings you can tweak.

## Architecture

### Component Hierarchy

The framework follows a hierarchical structure where experiments contain tasks, tasks contain blocks, and blocks contain trials:

```
┌─────────────────────────────────────────────────────────────────┐
│                         EXPERIMENT                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                        SENSORS                            │  │
│  │    (Run in parallel throughout the experiment)            │  │
│  │    ┌──────────┐  ┌──────────┐  ┌──────────┐              │  │
│  │    │EyeTracker│  │   EEG    │  │   EMG    │  ...         │  │
│  │    └──────────┘  └──────────┘  └──────────┘              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    PRACTICE TASKS                         │  │
│  │    ┌──────────┐  ┌──────────┐                            │  │
│  │    │  Task 1  │  │  Task 2  │  ...                       │  │
│  │    └──────────┘  └──────────┘                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      MAIN TASKS                           │  │
│  │    ┌──────────┐  ┌──────────┐  ┌──────────┐              │  │
│  │    │   MOT    │  │    VS    │  │ Custom   │  ...         │  │
│  │    └──────────┘  └──────────┘  └──────────┘              │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Task → Block → Trial Structure

Each task can contain multiple blocks, and each block contains multiple trials:

```
┌────────────────────────────────────────────────────────────┐
│                          TASK                              │
│                                                            │
│   initial_setup()  →  Prepare resources (windows, etc.)   │
│                                                            │
│   ┌────────────────────────────────────────────────────┐   │
│   │                     BLOCK 1                        │   │
│   │   ┌─────────┐  ┌─────────┐  ┌─────────┐           │   │
│   │   │ Trial 1 │→ │ Trial 2 │→ │ Trial 3 │→ ...      │   │
│   │   └─────────┘  └─────────┘  └─────────┘           │   │
│   │                                                    │   │
│   │   execute(order='predefined' | 'random')          │   │
│   └────────────────────────────────────────────────────┘   │
│                            ↓                               │
│   ┌────────────────────────────────────────────────────┐   │
│   │                     BLOCK 2                        │   │
│   │   ┌─────────┐  ┌─────────┐  ┌─────────┐           │   │
│   │   │ Trial 1 │→ │ Trial 2 │→ │ Trial 3 │→ ...      │   │
│   │   └─────────┘  └─────────┘  └─────────┘           │   │
│   └────────────────────────────────────────────────────┘   │
│                            ↓                               │
│                          ...                               │
└────────────────────────────────────────────────────────────┘
```

### Execution Flow

```
                    ┌──────────────┐
                    │  ray.init()  │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │  Experiment  │
                    │    .run()    │
                    └──────┬───────┘
                           ↓
         ┌─────────────────┴─────────────────┐
         ↓                                   ↓
┌─────────────────┐                 ┌─────────────────┐
│  Start Sensors  │                 │   (parallel)    │
│   (non-block)   │←───────────────→│  Push markers   │
└─────────────────┘                 └─────────────────┘
         │
         ↓
┌─────────────────┐
│ Practice Tasks  │ ←── TASK_START marker
│   (sequential)  │
└────────┬────────┘
         ↓
┌─────────────────┐
│   Main Tasks    │ ←── TASK_START marker
│   (sequential)  │
│                 │
│  ┌───────────┐  │
│  │  Block 1  │  │ ←── BLOCK_START marker
│  │  ┌─────┐  │  │
│  │  │Trial│  │  │ ←── TRIAL_START marker
│  │  └─────┘  │  │
│  └───────────┘  │
└────────┬────────┘
         ↓
┌─────────────────┐
│  Stop Sensors   │
└────────┬────────┘
         ↓
┌─────────────────┐
│ experiment      │
│   .close()      │
└─────────────────┘
```

### Class Relationships

```
                    ┌───────────────────┐
                    │    Experiment     │
                    │                   │
                    │ + add_task()      │
                    │ + register_sensor()│
                    │ + run()           │
                    │ + close()         │
                    └─────────┬─────────┘
                              │ contains
            ┌─────────────────┼─────────────────┐
            ↓                 ↓                 ↓
┌───────────────────┐ ┌───────────────┐ ┌───────────────┐
│   GeneralTask     │ │   LSLTask     │ │    Sensor     │
│   (abstract)      │ │               │ │   (abstract)  │
│                   │ │               │ │               │
│ + initial_setup() │ │ extends       │ │ + read_data() │
│ + add_block()     │ │ GeneralTask   │ │ + stream_data()│
│ + execute()       │ │               │ │ + push_marker()│
└─────────┬─────────┘ └───────────────┘ └───────────────┘
          │ contains
          ↓
┌───────────────────┐
│      Block        │
│                   │
│ + add_trial()     │
│ + execute()       │
│   (predefined/    │
│    random order)  │
└─────────┬─────────┘
          │ contains
          ↓
┌───────────────────┐
│      Trial        │
│    (abstract)     │
│                   │
│ + execute()       │
│ + get_data_signature()│
│ + stream_data()   │
└───────────────────┘
```

## Quick Start Example

Here's how to build a simple experiment:

```python
import ray
from ixp.experiment import Experiment
from ixp.task import GeneralTask, Block, Trial

# 1. Define your Trial
class MyTrial(Trial):
    def get_data_signature(self):
        return {
            'name': 'MyTrial',
            'type': 'none',  # 'none' for save-only (no LSL streaming)
            'channel_count': 1,
            'nominal_srate': 0,
            'channel_format': 'float32',
            'source_id': 'my_trial'
        }

    def execute(self):
        # Your trial logic here
        print(f"Running trial {self.trial_id}")
        return {"result": "success"}

# 2. Define your Task
class MyTask(GeneralTask):
    def __init__(self, config):
        super().__init__(config)

        # Create a block with trials
        block = Block('block_1')
        for i in range(5):
            trial = MyTrial(f'trial_{i}', config)
            block.add_trial(trial, order=i)
        self.add_block(block)

    def initial_setup(self):
        # Optional: Initialize resources (pygame window, etc.)
        pass

    def execute(self, order='predefined'):
        self.initial_setup()
        super().execute(order)  # Runs all blocks/trials

# 3. Run the Experiment
ray.init()

experiment = Experiment({'run_practice': False})

experiment.add_task(
    name='my_task',
    task_cls=MyTask,
    task_config={'param': 'value'},
    order=1
)

experiment.run()
experiment.close()
```

### Using Built-in Tasks

```python
from ixp.experiment import Experiment
from ixp.individual_difference.mot import MOT
from ixp.individual_difference.vs import VS

experiment = Experiment({'run_practice': True})

# Add Multiple Object Tracking task
experiment.add_task(
    name='mot',
    task_cls=MOT,
    task_config={
        'n_targets': 4,
        'n_distractors': 4,
        'n_trials': 10
    },
    order=1
)

# Add Visual Search task
experiment.add_task(
    name='vs',
    task_cls=VS,
    task_config={
        'grid_size': 6,
        'n_trials': 20
    },
    order=2
)

experiment.run()
```

## License

MIT — Do cool research with it.
