from __future__ import annotations

import ray

from ixp.runner import ExperimentRunner
from tests.examples import ExampleSensor, ExampleTask
from utils import skip_run

with skip_run('run', 'test_features') as check, check():
    # Initialize Ray
    ray.init(ignore_reinit_error=True)

    # Experiment configuration
    config = {'run_practice': False}

    # Create an instance of ExperimentRunner
    runner = ExperimentRunner(config)

    # Register a practice task
    runner.add_task(name='practice_1', task=ExampleTask, task_config={'name': '2'}, order=1, is_practice=True)

    # Register a main task
    runner.add_task(name='main_1', task=ExampleTask, task_config={'name': '1'}, order=2)

    # Register a sensor
    runner.register_sensor(name='temperature_sensor', sensor=ExampleSensor, sensor_config={'sensor_id': '1'})

    # Run the experiment
    runner.run()

    # Clean up
    runner.close()
