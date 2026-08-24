## Overall

All communications between frontend and backend are sent in the format of JSON via socket.

## Request

### Keys

- `action` The action to be conducted by the backend
- `source` The frontend that send this request. See complete list at constants.py:SOURCES
- `cwd` The current working directory of frontend. The missing of this key may cause error of a relative path is sent to back
- `token` Required when the backend has a non-empty `backend_token`. Frontends read it from `frontend_token`. See the `config` section below.
- Other keys depending on the action. A list of keys for each action can be seen at constants.py:ACTION_KEYS

## Response

### Response code

Key: `code`

- 0 OK. The main goal of the action successfully completed, though some additional goal (for example, auto set metadata of `lib add`) might have failed. In that case, the failed sub-goal should be visible in message.
- 1 Failed. Backend can not conduct this action. More information should be available in message.
- 2 Failed to connect to CADENCE backend. This response was not sent by backend but by client.py
- 3 Default code, should not be used under any circumstances. Receiving this code means gen_response.py:Response._response was accidentally called outside the class.
- 4 Exiting. Daemon-like frontend should exit immediately after receiving this code.
- 5 Authorization failed. The request token did not match the backend token. Sent by backend when `backend_token` is set and the request carries no or a wrong token.

### Message

Key: `msg`

A message about the result of the action. Only summarizing information may be shown in this message. Full results (for example, result of list sub-command) should be put under the `attachment` key.
For multi-stage actions such as replay (including jump to beginning and delete memorized position) the result of different stages should be separated by "|".

### Attachment

Key: `attachment`

A list or dictionary of information requested by the frontend.

### Failed actions

Key: `failed`

A list of messages of failed sub-actions during a batch action such as `lib.scan`.

## Actions

### config

Read and modify the configuration file. These actions operate on the options defined in `constants.py:CONFIG_SCHEME`, stored in `config.toml`.

#### Options

| Option | Type | Section | Default | Description |
|---|---|---|---|---|
| `username` | string | (root) | `J. Doe` | Name shown in the welcome message |
| `backend_token` | string | network | `` | Token for backend to verify requests with. Empty means authentication is disabled |
| `frontend_token` | string | network | `` | Token for frontend to send with |
| `backend_port` | port (int > 0) | network | `17891` | Port for backend to listen on |
| `backend_host` | string | network | `127.0.0.1` | Host for backend to listen on |
| `frontend_port` | port (int > 0) | network | `17891` | Port for frontend to send requests to |
| `frontend_host` | string | network | `127.0.0.1` | Host for frontend to send requests to |
| `ipc_timeout` | positive float | network | `10` | Timeout of frontend-backend communication (seconds) |
| `default_volume` | percentage (0~100) | playback | `100` | Volume on start |
| `default_shuffle` | boolean | playback | `false` | Shuffle mode on start |
| `pos_memorize_interval` | positive float | playback | `5` | Interval of memorized position updates (seconds) |
| `player_timeout` | positive float | playback | `1` | Timeout of backend waiting for a player action (seconds) |

The default value does not go through the type converter; values from the file are validated against the option type and fall back to the default if invalid.

Effective timing differs per option. `host` and `port` are read when the backend binds its socket; `default_volume`, `default_shuffle` and `username` are read at backend construction — changes to these need a backend restart. `ipc_timeout` is read on every connection, `player_timeout` on every player action, and `pos_memorize_interval` on every loop iteration — changes take effect without restart.

#### config.list

Request keys: none.

Success response attachment: a list of option info dicts (one per option in `CONFIG_SCHEME`), each shaped like `config.show`'s attachment.

#### config.show

Request keys: `option` (string, required).

Success response attachment: `{"name": <option name>, "value": <converted value>, "source": "default value" | "configure file", "default": <default value>, "description": <option description>}`. Unknown option is a failure.

#### config.set

Request keys: `option` (string, required), `value` (string, required), `overwrite_corrupt` (boolean, optional, default false).

Writes the option to the config file. Invalid values (wrong type or out of range) are rejected. `overwrite_corrupt` replaces a corrupted config file instead of failing.

#### config.unset

Request keys: `option` (string, required).

Removes the option from the config file so it falls back to its default value.

#### config.open

Request keys: none.

Opens the config file with the system's default application. If the file does not exist, an empty one is created first, then opened. Failure responses: no opener available on this platform, or failed to create the file.

#### config.path

Request keys: none.

Success response attachment: the path of the config file (string).

## The REAL Response codes

0 It's done. Probably
1 You fucked up
2 Nobody home
3 I fucked up
4 Fuck off, I'm dying