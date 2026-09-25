# CASCADE

**C**ommand-Line **A**udio **S**tream **C**apture **A**nd **D**ecoding **E**ngine

![CASCADE logo](res/musical.png)

Retrieves collections of mechanically-represented wave data from persistent storage, decompartmentalizes their format-specific encapsulation, reconstitutes the original waveform through algorithmic reconstruction, and transmits the resulting signal to a computer-connected mechanical wave generator. Controlled via a teletype-like interactive interface. Supports automatic transition to the next data set or the beginning of the current data set upon completion, based on a configured mode.

(CLI music player. Lives in the terminal.)

## Features

- Control your playback from the command line
- Memorized playback position — resume where you left off
- Shuffle & Loop mode — Random or repeat
- Volume and mute control
- Media key control
- Tray icon + TUI
- Real time lyric from local/online source
- Automatic lyric downloading
- Pluggable audio engine: VLC x miniaudio

## Dependencies

- Python 3.12+
- VLC media player (if you want to use the VLC engine)
- [Third-party packages](requirements.in)

## Installation

### Option A — pip (recommended)

Install straight from the repository (needs `git`):

```bash
pip install git+https://github.com/askformeal/CASCADE.git
```

Or from a downloaded copy, from the project directory:

```bash
git clone https://github.com/askformeal/CASCADE.git
cd CASCADE
pip install .
```

The `cascade` command will be available after installation.

For development, run from the repo root instead of installing:

```bash
python -m src
```

**With the `vlc` engine you must install [VLC](https://www.videolan.org/vlc/) yourself; the default `miniaudio` engine needs none.**

### Option B — portable build (`build.sh`)

```bash
bash build.sh          # on Windows: from git-bash
```

Builds a self-contained folder (plus a `.zip`) into `dist/cascade-<version>/`, bundling a standalone CPython runtime, all dependencies, **and the VLC runtime** (a GUI-free subset — see `VLC_SRC` in `build.sh`). Launch with `cascade.cmd` in the bundle root; it can be copied to another machine and run as-is.

**No VLC installation needed** — the bundle ships its own.

## CLI commands

### Lifecycle

| Command                 | Description                                |
| ----------------------- | ------------------------------------------ |
| `cascade start`       | Start the CASCADE backend                  |
| `cascade start -c`    | Start backend and resume last session      |
| `cascade start --dev` | Start backend with dev database            |
| `cascade reboot`      | Restart the backend                        |
| `cascade reboot -c`   | Restart and resume last session            |
| `cascade exit`        | Stop the backend                           |
| `cascade kill`        | Force-kill backend processes (last resort) |

### Playback

| Command                  | Description                                                       |
| ------------------------ | ----------------------------------------------------------------- |
| `cascade status`       | Show current playback status                                      |
| `cascade open <song>`  | Open a song, playlist, or file path                               |
| `cascade play-all`     | Play all songs in the library                                     |
| `cascade reload`       | Re-open the last playback session                                 |
| `cascade pause`        | Pause playback                                                    |
| `cascade resume`       | Resume playback                                                   |
| `cascade toggle`       | Switch between playing/paused                                     |
| `cascade stop`         | Stop playback                                                     |
| `cascade prev`         | Switch to the previous song                                       |
| `cascade next`         | Switch to the next song                                           |
| `cascade list`         | Show what is currently playing                                    |
| `cascade dice`         | Switch to a random song in current playlist                       |
| `cascade shuffle`      | Toggle shuffle                                                    |
| `cascade loop`         | Toggle loop                                                       |
| `cascade reverse`      | Toggle reverse playback                                           |
| `cascade lyric`        | Toggle lyric source (local / online)                              |
| `cascade switch <num>` | Switch to a song by number                                        |
| `cascade seek <time>`  | Jump to a specific time - relative jumping by adding a +/- prefix |
| `cascade jump <pct>`   | Jump to progress of the current song (percentage)                 |
| `cascade replay`       | Replay the current song                                           |
| `cascade volume <pct>` | Set volume (0-100) - relative setting by adding a +/- prefix      |
| `cascade mute`         | Toggle mute                                                       |

> Note: if negative time/volume is parsed as an option, wrap it in quotes like `cascade seek -1:30`

### Library

| Command                                  | Description                                                                                                                                                                       |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `cascade lib list`                     | Show all songs in library (`-a` aliases, `-p` playlists, `-t` tech metadata)                                                                                                |
| `cascade lib info <song>...`           | Show detailed info of songs (`-a` aliases, `-p` playlists, `-t` tech)                                                                                                       |
| `cascade lib search <kw>...`           | Search songs by name/artist/album/alias (`-o` match by OR)                                                                                                                      |
| `cascade lib add <path>...`            | Add new songs to library (`-a/--aliases` to bind aliases, `--loose-path` to allow missing paths, `--skip-meta`/`--skip-alias`/`--skip-lyric` to disable auto-detection) |
| `cascade lib del <song>...`            | Delete songs from library                                                                                                                                                         |
| `cascade lib scan <dir>`               | Scan a directory for audio files and add them (`-d` dry run, `--skip-meta`/`--skip-alias`/`--skip-lyric`)                                                                 |
| `cascade lib prune`                    | Delete all songs whose file no longer exists (`-d` dry run)                                                                                                                     |
| `cascade lib reset`                    | Reset library and delete all data                                                                                                                                                 |
| `cascade lib meta set`                 | Set metadata of a song                                                                                                                                                            |
| `cascade lib meta read-file`           | Set metadata of a song from its file tags (`--all` for every field)                                                                                                             |
| `cascade lib lyric show`               | Show the set lyric file of a song                                                                                                                                                 |
| `cascade lib lyric set`                | Set the lyric file of a song                                                                                                                                                      |
| `cascade lib lyric offset <song> <ms>` | Set a lyric time offset in milliseconds (positive delays the lyric, negative brings it earlier)                                                                                   |
| `cascade lib lyric fetch <song>...`    | Fetch lyrics from online sources                                                                                                                                                  |
| `cascade lib alias ...`                | List/bind/unbind aliases                                                                                                                                                          |
| `cascade lib playlist ...`             | List/create/add/kick/delete playlists (`lib playlist list` supports `-a`/`-p`/`-t`)                                                                                       |

`lib scan` will take in all files that is supported by **VLC**. If you are using `miniaudio` as audio engine you might not be able to play some of the files you scanned.

`lib lyric fetch` is easy to timeout, and even if that happens, backend will continue downloading and writing files in background. I recommend you not to fetch for more than four songs at a time, as four is the maximum parallel downloading allowed.

> **Note for China Mainland users:** when fetching lyrics online, it is recommended to enable `netease_skip_proxy`. If you are in there you'll know why.

You can reference a song by one of its aliases, its library ID or its file path. Pay caution that library ID is NOT fixed. It is basically its number in the database.

### Configuration

| Command                                 | Description                                                                                  |
| --------------------------------------- | -------------------------------------------------------------------------------------------- |
| `cascade config list`                 | Show information of all options                                                              |
| `cascade config show <option>`        | Show information of a specific option                                                        |
| `cascade config set <option> <value>` | Write an option to the config file (`--overwrite-corrupt` to replace a corrupted file)     |
| `cascade config unset <option>`       | Remove an option from the config file (falls back to default)                                |
| `cascade config gui`                  | Open the configure GUI                                                                       |
| `cascade config open`                 | Open the config file with the system's default application (creates an empty one if missing) |
| `cascade config path`                 | Show the path of the config file                                                             |

`config` commands accept `-d/--direct` to bypass the backend and edit the config file locally (works when the backend is not running, but cannot edit config files of remote backends). Its opposite, `--no-direct`, forces the backend route back on; passing neither leaves the choice to the command — for `config gui` that is the `config_default_remote` option.

> If you try to open the config file while connected to a remote backend, the file will be opened on the remote machine

See [docs/configuration.md](docs/configuration.md) for the config file and every option.

## Tray icon

The tray icon starts with the backend (unless the `tray` config option is off):

![Tray icon menu](res/tray_screenshot.png)

## Dashboard

The dashboard (`cascade dash`) is an interactive terminal UI.

```
╭──────────────────────────────────────┬────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────────╮
│  Information                         │               CASCADE 0.54.0 Dashboard                 │  Playlist                                                               │
│                                      │  ==================================================    │                                                                   0 ↑   │
│  Library ID: 16                      │                                                        │  > -[ Attero Dominatus ]- <                                             │
│                                      │               Attero Dominatus [1/160]                 │  Coat of Arms                                                           │
│  Duration: 00:03:43                  │                                                        │  Dominium Maris Baltici                                                 │
│                                      │  ████░░░░░░░░░░░░░░░░░░░░░░░░░░ [00:00:29/00:03:43]    │  Hellrider                                                              │
│  Name: Attero Dominatus              │                                                        │  Night Witches                                                          │
│  Artist: Sabaton                     │                                                        │  Primo Victoria                                                         │
│  Album: Attero Dominatus (Re-Armed)  │  ████████████████████ [100%]    [Ol Lyric] [Paused]    │  Templars                                                               │
│                                      │                                                        │  Sparta                                                                 │
│  Bitrate: 1051.179 kbps              │  ╭──────────────────────────────────────────────────╮  │  Stormtroopers                                                          │
│  Sample Rate: 44100                  │  │                     Interimo!                    │  │  Sun Tzu Says                                                           │
│  Channels: 2                         │  │                                                  │  │  The Future of Warfare                                                  │
│                                      │  │            -[ The reich has fallen ]-            │  │  Dreadnought                                                            │
│  Aliases:                            │  │                                                  │  │  Ghost Division                                                         │
│    Attero Dominatus                  │  │          We stand at the gates of Berlin         │  │  Last Dying Breath                                                      │
│                                      │  │          With two and a half million men         │  │  Midway                                                                 │
│  Playlists:                          │  ╰──────────────────────────────────────────────────╯  │  No Bullets Fly                                                         │
│    Attero Dominatus                  │  Play/Pause                                            │  Nuclear Attack                                                         │
│                                      │                                                        │                                                                 143 ↓   │
│  Audio Engine: Miniaudio             │                                                        │                                                                         │
╰──────────────────────────────────────┴────────────────────────────────────────────────────────┴─────────────────────────────────────────────────────────────────────────╯
```

(Yep, that's Sabaton you are seeing)

#### Key mapping:

| Key                            | Action                                                 |
| ------------------------------ | ------------------------------------------------------ |
| `Space`                      | Play / pause                                           |
| `Ctrl+A`                     | Play all songs in the library                          |
| `Ctrl+R`                     | Reload                                                 |
| `o`                          | Open song / playlist                                   |
| `/`                          | Filter the current playlist - match by name and artist |
| `g`                          | Jump to a specific time (`HH:MM:SS`)                 |
| `n` / `p`                  | Next / previous song                                   |
| `j` / `k`, `↑` / `↓` | Selection up / down                                    |
| `PgUp` / `PgDn`            | Selection page up / down                               |
| `Home` / `End`             | Select top / bottom                                    |
| `c`                          | Select currently playing song                          |
| `Enter`                      | Switch to the selected song                            |
| `x`                          | Stop                                                   |
| `d`                          | Jump to a random song                                  |
| `s`                          | Toggle shuffle                                         |
| `r`                          | Toggle loop                                            |
| `b`                          | Toggle reverse playback                                |
| `z`                          | Toggle the lyric source (local / online)               |
| `]` / `[`                  | Nudge the lyric offset overlay                         |
| `\`                          | Reset the lyric offset overlay                         |
| `f`                          | Toggle poster mode (full-screen album cover)           |
| `=` / `-`                  | Volume up / down                                       |
| `m`                          | Mute                                                   |
| `,` / `h`, `←`          | Jump backward                                          |
| `.` / `l`, `→`          | Jump forward                                           |
| `t` / `T`                  | Next / previous box style                              |
| `?` / `F1`                 | Show help                                              |
| `Ctrl+L`, `F5`             | Redraw                                                 |
| `q`, `Ctrl+C`, `Ctrl+Z`  | Quit                                                   |

## Lyric board

A floating lyric display.

![Floating lyric board](res/lyric_board_screenshot.png)

## Configure GUI

A desktop window that allows you to modify configurations conveniently

![Configure GUI](res/config_gui_screenshot.png)

## Lyric

### Offset

There are two types of offsets: one that is persisted in the database for each song and a temporary "offset overlay" that applies to all songs.

## Audio engines

There are TWO engines available: miniaudio and VLC.

[miniaudio](https://github.com/mackron/miniaudio) is lighter than VLC but does not support as many file formats.

If VLC is selected, the program will locate the runtime by:

1. Environment variable `PYTHON_VLC_LIB_PATH` (full path to `libvlc.dll`) and `PYTHON_VLC_MODULE_PATH` (plugin directory)
2. registry and the usual `Program Files\VideoLAN\VLC` locations
3. `libvlc.dll` next to the working directory

The portable package contains the runtime itself and will set the environment variables automatically.

## Data persistence

- Database: `%LOCALAPPDATA%\cascade\cascade\cascade.db` (Windows)
- Dev database: `%LOCALAPPDATA%\cascade\cascade\cascade-dev.db` (Windows) — used when the backend is started with `--dev`
- Audio formats: FLAC, MP3, WAV, and other common formats (see `AUDIO_EXTENSIONS` in `src/constants/misc.py`) — which of them actually decode depends on the engine ([Audio engines](#audio-engines))

## Logs

Log file folder location:

| Platform | Path                                                                          |
| -------- | ----------------------------------------------------------------------------- |
| Windows  | `%LOCALAPPDATA%\cascade\cascade\Logs\`                                      |
| Linux    | `$XDG_STATE_HOME/cascade/log/`, defaults to `~/.local/state/cascade/log/` |
| macOS    | `~/Library/Logs/cascade/`                                                   |

There are several log files for different modules

| Module           | Filename               |
| ---------------- | ---------------------- |
| Backend          | cascade.log            |
| IPC              | cascade-socket.log     |
| Media Key Daemon | cascade-hotkey.log     |
| System Tray      | cascade-tray.log       |
| Lyric Board      | cascade-lyric.log      |
| Dashboard        | cascade-dash.log       |
| Config GUI       | cascade-config-gui.log |
| Configure        | cascade-config.log     |
| PID Management   | cascade-pid.log        |
| Utils            | cascade-util.log       |

## TODO

See [TODO.md](TODO.md) for planned features.

## Credits

Icon: [Cadence icons created by Three musketeers - Flaticon](https://www.flaticon.com/free-icons/cadence)

Lyric icon: [Lyrics icons created by Aranagraphics - Flaticon](https://www.flaticon.com/free-icons/lyrics)

Cover placeholder: [Image-placeholder icons created by Graphics Plazza - Flaticon](https://www.flaticon.com/free-icons/image-placeholder)

Uicons by [Flaticon](https://www.flaticon.com/uicons)

## License

MIT License, because using it is your loss.
