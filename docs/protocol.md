## Overall

All communications between frontend and backend are sent in the format of JSON via socket.

## Request

### Keys

- `action` The action to be conducted by the backend
- `source` The frontend that send this request. See complete list at constants.py:SOURCES
- `cwd` The current working directory of frontend. The missing of this key may cause error of a relative path is sent to back
- `token` Required when the backend has a non-empty `backend_token`. Frontends read it from `frontend_token`. See the `config` section below.
- `silent` Optional. When true, the backend skips routine INFO logging for this request and its response. Intended for high-frequency polling (the tray polls `status`/`list` with it); errors are still logged.
- `notify_support` Optional. When true, the backend attaches any pending notifies to this request's response and clears them. Only frontends that consume notifies should set it (the CLI does; the tray and hotkey explicitly don't).
- Other keys depending on the action. A list of keys for each action can be seen at constants.py:ACTION_KEYS

### Acknowledge (ACK)

On receiving a request, the backend immediately replies with an ACK (`{"msg": "Copy that"}`) before running the action, then sends the actual `Response` when the action finishes. The ACK carries no `code`; it is only a liveness signal, letting the frontend distinguish "backend is still processing" from "backend died or never got the request". This lets long actions (e.g. `lib.lyric.fetch`) acknowledge quickly and take their time producing the response.

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

### poll

Collect everything a polling frontend needs in one round trip. The dashboard, the tray icon and the floating lyric board request it on every refresh cycle (0.1~1s), instead of combining `status`, `list`, `lib.info`, `lib.playlist.list` and the lyric state into separate requests. They send it with `silent` set, since it runs at a high frequency.

Request keys: none. In particular no `cwd` — a frontend that only displays the current state has no path to resolve.

Success response attachment: a dictionary combining

- the playback status fields, the same ones the `status` action returns: `id`, `path`, `name`, `artist`, `album`, `duration` (milliseconds), `bitrate`, `sample_rate`, `channels`, `lyric_path`, `in_library`, `player_status`, `volume`, `mute`, `shuffle`, `loop`, `online_lyric`, `playlist_len`, `current_num` (0-based number in the current playlist), `run_time` (seconds), `length` and `time` (milliseconds, -1 when unknown), `dev`
- the library information of the current song: `aliases` (a list of strings) and `added_playlists` (the names of the playlists holding it). Both are `null` when the current song is not in the library.
- the lyric state of the current song: `lyric` (a list of `[position in milliseconds, text]` pairs), `lyric_loading` (true while an online lyric is being fetched), `lyric_offset` (the offset stored for this song in the library) and `offset_overlay` (the offset the user adjusted on the fly)
- `current_songs`, the current playlist as a list of song info dictionaries (empty when nothing is playing)
- `playlists`, the names of every playlist in the library

Unknown values are sent as `null`; a frontend should treat a missing key the same way, since an older backend may not send it. How a frontend renders `null` is not part of the protocol — the dashboard substitutes a colored `[EMPTY]` marker, the other frontends show nothing.

`poll` supersedes `get_lyric`, which has been removed: instead of fetching the playback status, the library information and the lyric state with separate requests, frontends now read them from a single snapshot. Because an online lyric is fetched in a background thread, a frontend must keep polling to see it arrive (`lyric_loading` is true until it does).

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
| `connection_timeout` | positive float | network | `3` | Timeout of frontend waiting for the backend's acknowledge (seconds) |
| `execution_timeout` | positive float | network | `30` | Timeout of frontend waiting for the backend's response (seconds) |
| `hotkey` | boolean | service | `true` | Whether to start the hotkey service on backend start |
| `tray` | boolean | service | `true` | Whether to start the system tray icon service on backend start |
| `default_volume` | percentage (0~100) | playback | `100` | Volume on start |
| `default_shuffle` | boolean | playback | `false` | Shuffle mode on start |
| `pos_memorize_interval` | positive float | playback | `5` | Interval of memorized position updates (seconds) |
| `player_timeout` | positive float | playback | `1` | Timeout of backend waiting for a player action (seconds) |
| `dash_volume_step` | positive int | dash | `5` | Step of volume increase/decrease on dashboard |
| `dash_pos_step` | positive int | dash | `5` | Step of position forward/backward on dashboard |
| `escape_char` | boolean | appearance | `true` | Whether the CLI and dashboard output uses ANSI escape codes (colors) |
| `cli_box_style` | box style | appearance | `rounded` | Box style of CLI (`ascii`, `at`, `rounded`, `square`, `double-corner`, `heavy-corner`, `double`, `heavy`) |
| `dash_box_style` | box style | appearance | `rounded` | Box style of dashboard |

The default value does not go through the type converter; values from the file are validated against the option type and fall back to the default if invalid.

Effective timing differs per option. `host` and `port` are read when the backend binds its socket; `default_volume`, `default_shuffle` and `username` are read at backend construction — changes to these need a backend restart. `connection_timeout` (waiting for the ACK) and `execution_timeout` (waiting for the response) are read on every request, `player_timeout` on every player action, and `pos_memorize_interval` on every loop iteration — changes take effect without restart.

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