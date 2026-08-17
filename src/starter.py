import subprocess
import sys
import os
from time import sleep
from pathlib import Path
from src.client import test_alive
from src.constants import STARTER_RETRY, STARTER_CHECK_INTERVAL
from src.sentinels import SENTINELS

def start(**kwargs):
    if test_alive():
        return SENTINELS.BACKEND_ALREADY_RUNNING
    else:
        _spawn('src.backend', **kwargs)
        _spawn('src.hotkey')
        for i in range(STARTER_RETRY):
            if test_alive():
                return SENTINELS.BACKEND_STARTED
            sleep(STARTER_CHECK_INTERVAL)

        return SENTINELS.FAILED_START_BACKEND

def _spawn(module, **env_args):
    for key, value in env_args.items():
        env_args[key] = str(value)
    env = {**os.environ, **env_args}

    if sys.platform == 'win32':
        pythonw = sys.executable.replace('python.exe', 'pythonw.exe')
        if Path(pythonw).exists():
            exe = pythonw
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            exe = sys.executable
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        subprocess.Popen([exe, '-m', module], env=env, 
                            creationflags=flags,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            )
    else:
        args = [sys.executable, '-m', module]
        subprocess.Popen(args, env=env, 
                            start_new_session=True,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            )