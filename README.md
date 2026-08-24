# CADENCE

**C**ommand-line **A**udio **D**ecoding **E**ngine with **N**avigation and **C**ontinuous **E**xecution

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
| `cadence seek <time>`  | Jump to a specific time (HH:MM:SS)                     |
| `cadence jump <pct>`   | Jump to progress of the current song (percentage)      |
| `cadence replay`       | Clear memorized progress and replay the current song   |
| `cadence volume <pct>` | Set volume (0-100)                                     |
| `cadence mute`         | Toggle mute                                            |

### Library

| Command                     | Description                                        |
| --------------------------- | -------------------------------------------------- |
| `cadence lib list`          | Show all songs in library (`-a` aliases, `-p` playlists, `-t` tech metadata) |
| `cadence lib info <song>...`| Show detailed info of songs (`-a` aliases, `-p` playlists, `-t` tech) |
| `cadence lib search <kw>...`| Search songs by name/artist/album/alias (`-o` any-keyword match) |
| `cadence lib add <path>...`| Add new songs to library (`-a/--aliases` to bind aliases, `--loose-path` to allow missing paths) |
| `cadence lib del <song>...`| Delete songs from library (path, alias or ID)          |
| `cadence lib scan <dir>`    | Scan a directory for audio files and add them (`-d` dry run) |
| `cadence lib prune`         | Delete all songs whose file no longer exists (`-d` dry run)  |
| `cadence lib reset`         | Reset library and delete all data (confirmation)   |
| `cadence lib meta set`      | Set metadata of a song (use `""` to clear)         |
| `cadence lib meta read-file`| Set metadata of a song from its file tags (`--all` for every field) |
| `cadence lib alias ...`     | List/bind/unbind aliases (`bind <song> <alias>...`, `unbind <alias>...`) |
| `cadence lib playlist ...`  | List/create/add/kick/delete playlists (`lib playlist list` supports `-a`/`-p`/`-t`) |

`open` accepts a song alias, a library song name, a playlist name, or a file path.

### Configuration

| Command                        | Description                                            |
| ------------------------------ | ------------------------------------------------------ |
| `cadence config show <option>` | Show an option's value and its source (default/file)   |
| `cadence config set <option> <value>` | Write an option to the config file (`--overwrite-corrupt` to replace a corrupted file) |
| `cadence config unset <option>` | Remove an option from the config file (falls back to default) |

Config file: `%LOCALAPPDATA%\cadence\cadence\config.toml` (Windows). Full option list and semantics: [docs/protocol.md](docs/protocol.md).

## Architecture

- **Backend** (`src/backend.py`) — owns the VLC player and the SQLite database, listens on `127.0.0.1:17891` for JSON requests over a socket.
- **Frontend** (`src/cli.py`) — the `cadence` CLI. Sends action requests to the backend and formats responses.
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

Three log files: `cadence.log` (backend), `cadence-socket.log` (client/connection), `cadence-hotkey.log` (hotkey frontend).

## TODO

See [TODO.md](TODO.md) for planned features.

## License

MIT License, because using it is your loss.
