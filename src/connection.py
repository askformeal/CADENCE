import json

from src.log import setup_logger
from src.constants import SOCKET_LOG_PATH
from src.constants import HEADER_LEN, CONNECTION_ENCODING, MAX_JSON_SIZE
from src.sentinels import SENTINELS

logger = setup_logger(__name__, SOCKET_LOG_PATH)

def send_json(connection, data):
    try:
        data_bytes = json.dumps(data, ensure_ascii=False).encode(CONNECTION_ENCODING)
        length = len(data_bytes)
        connection.sendall(length.to_bytes(HEADER_LEN, byteorder='big'))
        connection.sendall(data_bytes)
        return True
    except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError) as e:
        logger.error(f'A socket error occurred during sending: {e}')
        return False

def recv_json(connection):
    raw_len = _recv_exact(connection, HEADER_LEN)
    if raw_len is SENTINELS.LOST:
        return None
    else:
        length = int.from_bytes(raw_len, byteorder='big')
        
        if length > MAX_JSON_SIZE:
            logger.error(f'JSON length {length} claimed in header is too large')
            return None

        elif length <= 0:
            logger.error(f'JSON length {length} claimed in header is invalid')
            return None

        else:
            raw_data = _recv_exact(connection, length)
            if raw_data is SENTINELS.LOST:
                logger.error('Connection lost')
                return None
            else:
                data = raw_data.decode(CONNECTION_ENCODING)
                try:
                    json_data = json.loads(data)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    logger.error('Invalid JSON received')
                    return None
                else:
                    return json_data

def _recv_exact(connection, length):
    data = b''
    while len(data) < length:
        try:
            chunk = connection.recv(length - len(data))
        except (ConnectionResetError, TimeoutError, OSError) as e:
            logger.error(f'A socket error occurred during receiving: {e}')
            return SENTINELS.LOST
        else:
            if not chunk:
                return SENTINELS.LOST
            data += chunk
    return data

'''
Protocols

response:

{
    'code': 0,
    'msg': 'success',
    'attachment': {}
}

'''
