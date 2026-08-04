import subprocess
import sys
import socket
from time import sleep
from pathlib import Path
from src.constants import HOST, PORT, TIMEOUT, STARTER_RETRY, STARTER_CHECK_INTERVAL
from src.sentinels import SENTINELS

def start():
    if _check_running():
        return SENTINELS.BACKEND_ALREADY_RUNNING
    else:
        if sys.platform == 'win32':
            pythonw = sys.executable.replace('python.exe', 'pythonw.exe')
            if Path(pythonw).exists():
                exe = pythonw
                flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                exe = sys.executable
                flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            subprocess.Popen([exe, '-m', 'src.backend'], creationflags=flags,
                             stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             )
        else:
            args = [sys.executable, '-m', 'src.backend']
            subprocess.Popen(args, start_new_session=True,
                             stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             )

        for i in range(STARTER_RETRY):
            if _check_running():
                return SENTINELS.BACKEND_STARTED
            sleep(STARTER_CHECK_INTERVAL)

        return SENTINELS.FAILED_START_BACKEND

def _check_running():
    try:
        sock = socket.create_connection((HOST, PORT), timeout=TIMEOUT)
    except socket.error:
        return False
    else:
        sock.close()
        return True