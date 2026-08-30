# CADENCE

**C**ommand-line **A**udio **D**ecoding **E**ngine with **N**avigation and **C**ontinuous **E**xecution

![CADENCE logo](res/musical.png)

Retrieves collections of mechanically-represented wave data from persistent storage, decompartmentalizes their format-specific encapsulation, reconstitutes the original waveform through algorithmic reconstruction, and transmits the resulting signal to a computer-connected mechanical wave generator. Controlled via a teletype-like interactive interface. Supports automatic transition to the next data set or the beginning of the current data set upon completion, based on a configured mode.

(CLI music player. Lives in the terminal.)

## Features

- Play songs, playlists, or your entire library from the command line
- Library with metadata (including duration), aliases, and playlists (persisted in SQLite)
- Auto metadata extraction and alias binding from file tags
- Memorized playback position — resume where you left off
- Shuffle mode
- Loop mode — replay the current song on end
- Random song jump (`dice`)
- Dev mode — isolated development database
- Volume and mute control
- Hotkey frontend (pynput)
- Tray icon frontend (pystray): playback controls, song/playlist switching, volume presets, now-playing tooltip and error indicator
- Dashboard frontend (`cadence dash`): interactive TUI with live status, playlist browsing and keyboard controls
- Socket-based backend/frontend architecture (see [docs/protocol.md](docs/protocol.md))

## Installation

Requires Python 3.12+.

```bash
pip install .
```

The `cadence` command will be available after installation. For development, run from the repo root:

```bash
python -m src
```

## Usage

### Lifecycle

| Command                   | Description                          |
| ------------------------- | ------------------------------------ |
| `cadence start`           | Start the CADENCE backend (daemon)   |
| `cadence start -c`        | Start backend and resume last session|
| `cadence start --dev`     | Start backend with dev database      |
| `cadence reboot`          | Restart the backend                  |
| `cadence reboot -c`       | Restart and resume last session      |
| `cadence exit`            | Stop the backend                     |
| `cadence kill`            | Force-kill backend processes (last resort) |
| `cadence status`          | Show current playback status         |

### Playback

| Command                | Description                                            |
| ---------------------- | ------------------------------------------------------ |
| `cadence open <song>`  | Open a song, playlist, or file path                    |
| `cadence play-all`     | Play all songs in the library                          |
| `cadence pause`        | Pause playing media                                    |
| `cadence resume`       | Resume paused media                                    |
| `cadence toggle`       | Switch between playing and paused                      |
| `cadence stop`         | Stop playing                                           |
| `cadence prev`         | Switch to the previous song in current playlist        |
| `cadence next`         | Switch to the next song in current playlist            |
| `cadence list`         | Show current playlist                                  |
| `cadence dice`         | Switch to a random song in current playlist            |
| `cadence shuffle`      | Toggle shuffle mode                                    |
| `cadence loop`         | Toggle loop mode                                       |
| `cadence switch <num>` | Switch to a song in current playlist via number        |
| `cadence seek <time>`  | Jump to a specific time, or seek relative to the current position with a `+`/`-` prefix (e.g. `seek +10` forward, `seek -10` backward) |
| `cadence jump <pct>`   | Jump to progress of the current song (percentage)      |
| `cadence replay`       | Clear memorized progress and replay the current song   |
| `cadence volume <pct>` | Set volume (0-100), or adjust relatively with a `+`/`-` prefix (e.g. `volume +5`, `volume -5`) |
| `cadence mute`         | Toggle mute                                            |

Note: a negative seek time starts with `-`, which the command-line parser treats as an option flag — quote it to pass it through, e.g. `cadence seek "-1:30"`. Plain numbers like `seek -10` work without quotes.

### Library

| Command                     | Description                                        |
| --------------------------- | -------------------------------------------------- |
| `cadence lib list`          | Show all songs in library (`-a` aliases, `-p` playlists, `-t` tech metadata) |
| `cadence lib info <song>...`| Show detailed info of songs (`-a` aliases, `-p` playlists, `-t` tech) |
| `cadence lib search <kw>...`| Search songs by name/artist/album/alias (`-o` any-keyword match) |
| `cadence lib add <path>...`| Add new songs to library (`-a/--aliases` to bind aliases, `--loose-path` to allow missing paths, `--skip-meta`/`--skip-alias`/`--skip-lyric` to disable auto-detection) |
| `cadence lib del <song>...`| Delete songs from library (path, alias or ID)          |
| `cadence lib scan <dir>`    | Scan a directory for audio files and add them (`-d` dry run, `--skip-meta`/`--skip-alias`/`--skip-lyric`) |
| `cadence lib prune`         | Delete all songs whose file no longer exists (`-d` dry run)  |
| `cadence lib reset`         | Reset library and delete all data (confirmation)   |
| `cadence lib meta set`      | Set metadata of a song (use `""` to clear)         |
| `cadence lib meta read-file`| Set metadata of a song from its file tags (`--all` for every field) |
| `cadence lib lyric set`     | Set the lyric file of a song (use `""` to unset)   |
| `cadence lib alias ...`     | List/bind/unbind aliases (`bind <song> <alias>...`, `unbind <alias>...`) |
| `cadence lib playlist ...`  | List/create/add/kick/delete playlists (`lib playlist list` supports `-a`/`-p`/`-t`) |

`open` accepts a song alias, a library song name, a playlist name, or a file path.

### Configuration

| Command                        | Description                                            |
| ------------------------------ | ------------------------------------------------------ |
| `cadence config list` | Show information of all options |
| `cadence config show <option>` | Show information of an option |
| `cadence config set <option> <value>` | Write an option to the config file (`--overwrite-corrupt` to replace a corrupted file) |
| `cadence config unset <option>` | Remove an option from the config file (falls back to default) |
| `cadence config open` | Open the config file with the system's default application (creates an empty one if missing) |
| `cadence config path` | Show the path of the config file |

`config` commands accept `-d/--direct` to bypass the backend and edit the config file locally (works when the backend is not running).

Config file: `%LOCALAPPDATA%\cadence\cadence\config.toml` (Windows). Options:

| Option | Default | Description |
| --- | --- | --- |
| `username` | `J. Doe` | Name shown in the welcome message |
| `backend_host` / `backend_port` | `127.0.0.1` / `17891` | Address the backend listens on |
| `frontend_host` / `frontend_port` | `127.0.0.1` / `17891` | Address the frontend sends requests to |
| `ipc_timeout` | `10` | Timeout of frontend-backend communication (seconds) |
| `default_volume` | `100` | Volume on start (0~100) |
| `default_shuffle` | `false` | Shuffle mode on start |
| `player_timeout` | `1` | Timeout of backend waiting for a player action (seconds) |
| `pos_memorize_interval` | `5` | Interval of memorized position updates (seconds) |

Values are validated on write; invalid ones are rejected. The default value is used when an option is not set or the stored value is invalid.

### Tray icon

The tray icon starts with the backend (unless the `tray` config option is off) and offers:

- Now-playing label and dynamic tooltip (song name + player status)
- Open — pick a song file with a file dialog (all supported audio types)
- Play/Pause (double-click), Previous/Next, Stop, Dice, Replay
- Switch submenu — jump to any song in the current playlist
- Playlists submenu — open any library playlist by name (plus `[Play All]`)
- Volume presets (0/25/50/75/100%), Mute, checkable Shuffle/Loop states
- The icon switches to an error variant for 1.5 s after a failed request

### Dashboard

The dashboard (`cadence dash`) is an interactive terminal UI. It shows the current song, a progress bar with elapsed/total time, volume bar and playback state, the current lyric line (if the song has a lyric file set via `cadence lib lyric set`), the playlist (with the playing song and your selection highlighted), and is controlled entirely from the keyboard. It starts its own frontend process and uses the same socket protocol as the other frontends.

Keys (defined in `DASH_KEY_MAP` in `src/constants.py`):

| Key | Action |
| --- | --- |
| `Space` | Play / pause |
| `Ctrl+A` | Play all songs in the library |
| `o` | Open a song — prompts for a song name, library ID, file path or playlist name |
| `/` | Filter the playlist — prompts for text, matches against song name and artist; highlights matches and shows remaining counts above/below |
| `g` | Jump to a specific time — prompts for `HH:MM:SS` |
| `n` / `p` | Next / previous song |
| `j` / `k`, `↑` / `↓` | Move selection up / down |
| `PgUp` / `PgDn` | Page selection up / down |
| `c` | Jump selection to the currently playing song |
| `Enter` | Play the selected song |
| `x` / `d` | Stop / random song jump |
| `s` / `r` | Toggle shuffle / loop |
| `=` / `-` | Volume up / down (step from `dash_volume_step`) |
| `m` | Mute |
| `,` / `h`, `←` | Jump backward (step from `dash_pos_step`) |
| `.` / `l`, `→` | Jump forward (step from `dash_pos_step`) |
| `t` / `T` | Next / previous box style (runtime only, not persisted) |
| `?` / `F1` | Toggle the key map help screen |
| `Ctrl+L`, `F5` | Redraw the screen |
| `q`, `Ctrl+C`, `Ctrl+Z` | Quit the dashboard |

## Architecture

- **Backend** (`src/backend.py`) — owns the VLC player and the SQLite database, listens on `127.0.0.1:17891` for JSON requests over a socket.
- **Frontends** — `src/cli.py` (the `cadence` CLI), `src/hotkey.py` (media key hotkeys), `src/tray.py` (system tray icon), `src/dash.py` (interactive dashboard). They send action requests to the backend and format responses.
- **Protocol** — all communication is JSON over a length-prefixed socket connection. See [docs/protocol.md](docs/protocol.md).

## Data

- Database: `%LOCALAPPDATA%\cadence\cadence\cadence.db` (Windows) — managed by platformdirs
- Dev database: `%LOCALAPPDATA%\cadence\cadence\cadence-dev.db` (Windows) — used when the backend is started with `--dev`
- Audio formats: FLAC, MP3, WAV, and other common formats (see `AUDIO_EXTENSIONS` in `src/constants.py`)

## Logs

Log file location (platform-dependent, managed by platformdirs):

| Platform | Path                                                                                                |
| -------- | --------------------------------------------------------------------------------------------------- |
| Windows  | `%LOCALAPPDATA%\cadence\cadence\Logs\cadence.log`                                                 |
| Linux    | `$XDG_STATE_HOME/cadence/log/cadence.log`, defaults to `~/.local/state/cadence/log/cadence.log` |
| macOS    | `~/Library/Logs/cadence/cadence.log`                                                              |

Log files: `cadence.log` (backend), `cadence-socket.log` (client/connection), `cadence-hotkey.log` (hotkey frontend), `cadence-tray.log` (tray frontend), `cadence-dash.log` (dashboard frontend), plus `cadence-config.log` and `cadence-pid.log`.

## TODO

See [TODO.md](TODO.md) for planned features.

## Credits

Icon: [Cadence icons created by Three musketeers - Flaticon](https://www.flaticon.com/free-icons/cadence)

## License

MIT License, because using it is your loss.
