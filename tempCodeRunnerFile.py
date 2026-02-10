with skip_run('run', 'multi_object_tracking') as check, check():
    ray.init(ignore_reinit_error=True)

    # Create an instance of ExperimentRunner
    runner = ExperimentRunner(config)
    # Register a practice task
    runner.add_task(name='multi_object_tracking', task_cls=MOT, task_config={'config': config['mot']}, order=1)
    runner.add_task(name='visual_search', task_cls=VS, task_config={'config': config['vs']}, order=2)
   
   
    class NoOpTask(GeneralTask):