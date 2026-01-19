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

| Task | What It Does |
|------|--------------|
| **MOT** (Multiple Object Tracking) | "Keep your eyes on the ball"—except there are 8 of them and they're all moving |
| **VS** (Visual Search) | Find the T among the Ls. Sounds easy until it isn't |

## Getting Started

### Installation

**From GitHub (pip):**

```shell
pip install git+https://github.com/elaheoveisi/ixp.git
```

**For development (Poetry):**

```shell
git clone https://github.com/elaheoveisi/ixp.git
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

## License

MIT — Do cool research with it.
