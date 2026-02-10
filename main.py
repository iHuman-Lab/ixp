from __future__ import annotations

from pathlib import Path

import ray
import yaml

from ixp.individual_difference import MOT, VS
from ixp.runner import ExperimentRunner
from ixp.task import GeneralTask
from tests.examples import ExampleSensor, ExampleTask
from utils import skip_run

with Path.open('ixp/configs/config.yaml') as f:
	config = yaml.safe_load(f)

with skip_run('skip', 'test_features') as check, check():
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


with skip_run('run', 'multi_object_tracking') as check, check():
	ray.init(ignore_reinit_error=True)

	# Create an instance of ExperimentRunner
	runner = ExperimentRunner(config)
	# Register a practice task
	runner.add_task(name='multi_object_tracking', task_cls=MOT, task_config={'config': config['mot']}, order=1)
	runner.add_task(name='visual_search', task_cls=VS, task_config={'config': config['vs']}, order=2)
   
   
	class NoOpTask(GeneralTask):
		def __init__(self, config):
			super().__init__(config)

		def execute(self):
			return None

	runner.add_task(name='questionnaire_placeholder', task_cls=NoOpTask, task_config={'config': {}}, order=3)

	# Run the experiment
	runner.run()

	# Close Ray resources then run the questionnaire in the main process
	try:
		runner.close()
	except Exception:
		pass

	try:
		from ixp.individual_difference.surveys.questionnaire import run_survey

		run_survey()
	except Exception:
		print('Warning: survey could not be run interactively.')

	# Minimal NASA-TLX block: prefer PsychoPy class, fallback to pygame class.
	import traceback

	try:
		try:
			from ixp.Surveys.nasa_tlx_psychopy import NASA_TLX as NASA_PSY_CLASS

			NASA_PSY_CLASS({}).execute()
		except Exception:
			# PsychoPy may fail on some systems (Qt DLL issues); try pygame-based UI
			traceback.print_exc()
			from ixp.Surveys.nasa_tlx_pygame import NASA_TLX as NASA_PG_CLASS

			NASA_PG_CLASS({}).execute()
	except Exception:
		print('NASA-TLX survey could not be run interactively. See traceback:')
		traceback.print_exc()

