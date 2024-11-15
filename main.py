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

    # Sensors
    sensor_config = {
        'source_id': '1',
        'name': 'temperature',
        'type': 'continous',
        'nominal_srate': 1.0,
        'channel_format': 'float32',
        'channel_count': 1,
    }
    temperature_sensor = ExampleSensor(sensor_config)
    runner.register_sensor(name='temperature_sensor', sensor=temperature_sensor)

    # Example task
    practice_task = ExampleTask({'name': '2'})
    # Register a practice task
    runner.add_task(name='practice_1', task=practice_task, order=1, is_practice=True)

    # Register a main task
    main_task = ExampleTask({'name': '1'})
    runner.add_task(name='main_1', task=main_task, order=2)

    # Run the experiment
    runner.run()

    # Clean up
    runner.close()
