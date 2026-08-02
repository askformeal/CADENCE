import logging
import socket

from src.constants import HOST, PORT, TIMEOUT
from src.connection import send_json, recv_json

logger = logging.getLogger(__name__)

def send_request(**kwargs):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect((HOST, PORT))
        if send_json(sock, kwargs):
            response = recv_json(sock)
            if response is not None:
                sock.close()
                return response
            else:
                sock.close()
                logger.error('Failed receive response from CADENCE backend')
        else:
            sock.close()
            logger.error('Failed to send message to CADENCE backend')

    except (ConnectionRefusedError, OSError) as e:
        return {
            'code': 1,
            'msg': f'A socket error occurred while trying to connect to CADENCE backend: {e}',
            'attachment': {}
        }