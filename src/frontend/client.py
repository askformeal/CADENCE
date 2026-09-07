import socket
from time import sleep

from src.log import setup_logger
from src.constants import SOCKET_LOG_PATH
from src.constants import DEATH_CONFIRM_INTERVAL, DEATH_CONFIRM_NUMBER
from src.config import CONFIG
from src.connection import send_json, recv_json

logger = setup_logger(__name__, SOCKET_LOG_PATH)

def send_request(expect_reset=False, **kwargs):
    try:
        kwargs['token'] = CONFIG.frontend_token
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(CONFIG.connection_timeout)
        sock.connect((CONFIG.frontend_host, CONFIG.frontend_port))
        if send_json(sock, kwargs, expect_reset=expect_reset):
            ack = recv_json(sock, expect_reset=expect_reset)
            if ack is None:
                logger.error('IPC failure during connection')
                sock.close()
                return {'code': 2, 'msg': 'IPC failure during connection', 'attachment': {}} 
            else:
                sock.settimeout(CONFIG.execution_timeout)
                response = recv_json(sock, expect_reset=expect_reset)
                sock.close()
                if response is None:
                    if not expect_reset:
                        logger.error('IPC failure during execution')
                    return {'code': 2, 'msg': 'IPC failure during execution', 'attachment': {}} 
                else:
                    return response
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
    response = send_request(action='test_alive', source='alive', notify_support=False, expect_reset=True)
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

def handle_code(code, callback):
    if code == 4:
        logger.info('Backend existing')
        callback()
    elif code == 5:
        logger.info('Authorization failed')
        callback()
    elif code == 2:
        if confirm_dead():
            logger.info('Death confirmed')
            callback()
        else:
            logger.info('Heartbeat resumed')