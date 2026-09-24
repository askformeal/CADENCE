## Overall

All communications between frontend and backend are sent in the format of JSON via socket.

## Request

### Keys

- `action` The action to be conducted by the backend
- `source` The frontend that send this request. See complete list at src/constants/network.py:SOURCES
- `cwd` The current working directory of frontend. The missing of this key may cause error of a relative path is sent to back
- `token` Required when the backend has a non-empty `backend_token`. Frontends read it from `frontend_token`. See the `config` section below.
- `silent` Optional. When true, the backend skips routine INFO logging for this request and its response. Intended for high-frequency polling (the tray polls `status`/`list` with it); errors are still logged.
- `notify_support` Optional. When true, the backend attaches any pending notifies to this request's response and clears them. Only frontends that consume notifies should set it (the CLI does; the tray and hotkey explicitly don't).
- Other keys depending on the action. A list of keys for each action can be seen at src/constants/network.py:ACTION_KEYS

### Acknowledge (ACK)

On receiving a request, the backend immediately replies with an ACK (`{"msg": "Copy that"}`) before running the action, then sends the actual `Response` when the action finishes. The ACK carries no `code`; it is only a liveness signal, letting the frontend distinguish "backend is still processing" from "backend died or never got the request". This lets long actions (e.g. `lib.lyric.fetch`) acknowledge quickly and take their time producing the response.

## Response

### Response code

Key: `code`

- 0 OK. The main goal of the action successfully completed, though some additional goal (for example, auto set metadata of `lib add`) might have failed. In that case, the failed sub-goal should be visible in message.
- 1 Failed. Backend can not conduct this action. More information should be available in message.
- 2 Failed to connect to CASCADE backend. This response was not sent by backend but by client.py
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

- the playback status fields, the same ones the `status` action returns: `id`, `path`, `name`, `artist`, `album`, `duration` (milliseconds), `bitrate`, `sample_rate`, `channels`, `lyric_path`, `in_library`, `player_status`, `volume`, `mute`, `shuffle`, `loop`, `reverse`, `online_lyric`, `engine` (the engine in use, `vlc` or `miniaudio`), `playlist_len`, `current_num` (0-based number in the current playlist), `run_time` (seconds), `length` and `time` (milliseconds, -1 when unknown), `dev`
- the library information of the current song: `aliases` (a list of strings) and `added_playlists` (the names of the playlists holding it). Both are `null` when the current song is not in the library.
- the lyric state of the current song: `lyric` (a list of `[position in milliseconds, text]` pairs), `lyric_loading` (true while an online lyric is being fetched), `lyric_offset` (the offset stored for this song in the library) and `offset_overlay` (the offset the user adjusted on the fly)
- `current_songs`, the current playlist as a list of song info dictionaries (empty when nothing is playing)
- `playlists`, the names of every playlist in the library
- `cover_hash`, the SHA-256 of the bytes `get_cover` would serve for the current song (`null` when it has no usable cover)

Unknown values are sent as `null`; a frontend should treat a missing key the same way, since an older backend may not send it. How a frontend renders `null` is not part of the protocol — the dashboard substitutes a colored `[EMPTY]` marker, the other frontends show nothing.

`poll` supersedes `get_lyric`, which has been removed: instead of fetching the playback status, the library information and the lyric state with separate requests, frontends now read them from a single snapshot. Because an online lyric is fetched in a background thread, a frontend must keep polling to see it arrive (`lyric_loading` is true until it does).

### get_cover

Hand over the current song's cover art. Request keys: none — the cover belongs to the song being played, so there is nothing to look up.

Success response attachment: `{"cover": <base64 of a JPEG image>}`.

The backend reads the cover when the playing song changes (from the file's own tags, or from a `cover.jpg` / `folder.jpg` / `album.jpg` / `albumart.jpg` / `front.jpg` next to it) and keeps it in memory, so repeated requests cost no disk access. Before serving it, the image is downscaled so that its longest side is at most `MAX_COVER_SIDE` (512 px, src/constants/backend.py) and re-encoded as JPEG at `COVER_QUALITY` (85) — a 1400x1400 cover shrinks from ~170 KB to ~48 KB, which is what a frontend actually needs: the dashboard's poster mode draws it as 80x64 half-block cells. A cover already smaller than the limit is passed through untouched, never upscaled.

Failure responses: the current song has no cover, or the cover could not be decoded (a corrupt, truncated or unsupported image — a `cover.jpg` that is not really an image gets here). Frontends are expected to fall back to a placeholder of their own in both cases; the dashboard bundles one in `res/no_cover.txt`.

`cover_hash` in the `poll` snapshot is the SHA-256 of exactly the bytes this action serves. A frontend caches the bytes it received and only asks again when the hash changes, which is why the poll never carries the image itself. Note that the hash describes the *served* bytes, not the original file: two songs with the same cover serve the same bytes and share a hash.

The cover is remembered even when playback stops — there is no current song whose cover would replace it — so `get_cover` keeps returning the last song's cover until something else plays.

### config

Read and modify the configuration file. These actions operate on the options defined in `src/constants/config.py:CONFIG_SCHEME`, stored in `config.toml`.

#### Options

Options are grouped into TOML sections in `config.toml` — `[network]`, `[service]`, `[playback]`, `[dash]`, `[appearance]`, `[lyric]` and `[config_gui]` — except `username`, which sits at the root of the file. The table below lists every option in the order `config.list` returns them.

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
| `execution_timeout` | positive float | network | `30` | Timeout of frontend waiting for the backend's response (seconds); keep it above `player_timeout` |
| `proxy` | string | network | `` | Proxy used when fetching lyrics online; empty uses the system default |
| `netease_skip_proxy` | boolean | network | `false` | Connect to the NetEase lyric source directly, ignoring `proxy` |
| `hotkey` | boolean | service | `true` | Whether to start the hotkey service on backend start |
| `tray` | boolean | service | `true` | Whether to start the system tray icon service on backend start |
| `lyric` | boolean | service | `true` | Whether to start the lyric board service on backend start |
| `engine` | choice (`vlc`, `miniaudio`) | playback | `vlc` | Audio engine used for playback. See the README's "Audio engines" section |
| `default_volume` | percentage (0~100) | playback | `100` | Volume on start |
| `default_shuffle` | boolean | playback | `false` | Shuffle mode on start |
| `default_online_lyric` | boolean | playback | `false` | Use the online lyric source on start |
| `pos_memorize_interval` | positive float | playback | `5` | Interval of memorized position updates (seconds) |
| `player_timeout` | positive float | playback | `1` | Timeout of backend waiting for a player action (seconds); keep it below `execution_timeout` |
| `dash_volume_step` | positive int | dash | `5` | Step of volume increase/decrease on dashboard |
| `dash_pos_step` | positive int | dash | `5` | Step of position forward/backward on dashboard |
| `escape_char` | boolean | appearance | `true` | Whether the CLI and dashboard output uses ANSI escape codes (colors) |
| `cli_box_style` | box style | appearance | `rounded` | Box style of CLI (`ascii`, `at`, `rounded`, `square`, `double-corner`, `heavy-corner`, `double`, `heavy`) |
| `dash_box_style` | box style | appearance | `rounded` | Box style of dashboard |
| `dash_poster_width` | positive int | appearance | `80` | Width of album cover on dashboard (columns) |
| `dash_poster_height` | positive int | appearance | `64` | Height of album cover on dashboard (pixels / 2 rows) |
| `dash_screen_buffer` | boolean | appearance | `true` | Whether to use the alt screen buffer for the dashboard |
| `auto_dash_height` | boolean | appearance | `true` | Whether to size the dashboard height from the terminal height |
| `pause_hide_lyric` | boolean | lyric | `true` | Whether to hide the lyric board when playback is paused |
| `lyric_hover_solid` | boolean | appearance | `true` | Whether the lyric board turns fully opaque with a solid background when hovered |
| `lyric_trans_bg` | boolean | appearance | `false` | Whether to use a fully transparent (color-keyed) window background instead of an opaque backdrop |
| `lyric_height` | non-negative int | appearance | `70` | Height of the lyric board (pixels) |
| `lyric_x_offset` | int | appearance | `0` | Horizontal offset of the lyric board from screen center (pixels, negative = left, positive = right) |
| `lyric_font_family` | string | appearance | `` | Font family of the lyric board (empty = system default) |
| `lyric_font_size` | non-negative int | appearance | `20` | Font size of the lyric board |
| `lyric_font_bold` | boolean | appearance | `false` | Whether to use a bold font on the lyric board |
| `lyric_font_color` | hex color | appearance | `#797979` | Font color of the lyric board (hex) |
| `lyric_bg_color` | hex color | appearance | `#111111` | Solid background color of the lyric board shown on hover (hex) |
| `lyric_opacity` | percentage (0~100) | appearance | `40` | Lyric board opacity when not hovered (100 = fully opaque) |
| `config_default_remote` | boolean | config_gui | `true` | Whether the configure GUI starts in remote mode |

Types are enforced by the converters in `src/types.py`; a value that does not satisfy its type is rejected on `config.set` and falls back to the default when read from a hand-edited file. The default value itself does not go through the converter.

Effective timing differs per option. Every access re-reads the config file, so an option that is consulted while running (the timeouts, `player_timeout`, `pos_memorize_interval`, the dashboard steps) takes effect immediately. What is read once, while something is being built, keeps its value until that component is restarted: the hosts and ports when the backend binds its socket, `engine`, `default_volume`, `default_shuffle`, `default_online_lyric` and `username` when the backend constructs its player, the service switches (`hotkey`, `tray`, `lyric`) when the CLI starts the frontends, the configure GUI's remote flag when its window is created, and the lyric board's font, size and geometry when its window is created.

The CLI can also operate on the config file without the backend, with `cascade config … --direct`; the actions above are the backend-side path, which is what a remote frontend uses, and `--no-direct` selects it explicitly.

#### config.list

Request keys: none.

Success response attachment: a list of option info dicts (one per option in `CONFIG_SCHEME`), each shaped like `config.show`'s attachment.

#### config.show

Request keys: `option` (string, required).

Success response attachment: `{"name": <option name>, "type": <type name>, "value": <converted value>, "source": "default value" | "configure file", "default": <default value>, "description": <option description>}`. Unknown option is a failure.

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