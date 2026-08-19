import socket
from time import sleep

from src.log import setup_logger
from src.constants import SOCKET_LOG_PATH
from src.constants import HOST, PORT, TIMEOUT
from src.constants import DEATH_CONFIRM_INTERVAL, DEATH_CONFIRM_NUMBER
from src.connection import send_json, recv_json

logger = setup_logger(__name__, SOCKET_LOG_PATH)

def send_request(expect_reset=False, **kwargs):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect((HOST, PORT))
        if send_json(sock, kwargs, expect_reset=expect_reset):
            response = recv_json(sock, expect_reset=expect_reset)
            if response is not None:
                sock.close()
                return response
            else:
                sock.close()
                if not expect_reset:
                    logger.error('Failed to receive response from CADENCE backend')
                return {'code': 2, 'msg': 'failed receive response from CADENCE backend', 'attachment': {}} 
            # code 0: everything's ok. code 1: backend failed to complete this action. code 2: can not connect to backend
        else:
            sock.close()
            if not expect_reset:
                logger.error('Failed to send message to CADENCE backend')
            return {'code': 2, 'msg': 'failed to send message to CADENCE backend', 'attachment': {}}

    except (ConnectionRefusedError, OSError) as e:
        return {
            'code': 2,
            'msg': f'A socket error occurred while trying to connect to CADENCE backend: {e}',
            'attachment': {}
        }

def test_alive():
    response = send_request(action='test_alive', source='alive', expect_reset=True)
    return response['code'] != 2

def test_heartbeat():
    response = send_request(action='heartbeat', source='heartbeat') # for good measure
    return response['code']

def confirm_dead():
    for i in range(DEATH_CONFIRM_NUMBER):
        sleep(DEATH_CONFIRM_INTERVAL)
        if test_heartbeat() == 0:
            return False # Brain~~~~~~
    return True