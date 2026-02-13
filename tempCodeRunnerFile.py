
with skip_run('run', 'sart') as check, check():
    SART(config.get('sart', {})).execute()