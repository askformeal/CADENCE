# CHANGELOG

## [0.6.0] - 2026-08-17

### Added

- Dev mode — `cadence start --dev` uses a separate development database (`cadence-dev.db`)

## [0.5.0] - 2026-08-17

### Added

- `loop` command — toggle loop mode (replay the current song on end)

## [0.4.0] - 2026-08-17

### Added

- `dice` command — switch to a random song in the current playlist
- `play-all` command — play all songs in the library
- Expanded README and TODO list

## [0.3.0] - 2026-08-16

### Added

- `lib.scan` command with `recurse`, `playlist`, and `skip` options
- Memorized playback position — resume on `open`/`switch`, restart on `prev`/`next`; `restart` command
- Song metadata (`name`/`artist`/`album`) with `lib.meta set`, auto-extracted from files on `lib add`
- `switch` command — switch to a song in the current playlist by number
- `jump` command — seek by percentage of the current song
- `lib.playlist del` and song listing in `lib.playlist list`
- Shuffle mode with shuffled playback order
- Volume and mute controls
- Hotkey frontend skeleton with play-dead shutdown lifecycle; media key control via pynput
- `reboot` command
- Log flush to disk on every write

### Changed

- Request key validation via `ACTION_KEYS` protocol contract (`invalid_key_type`)
- Response layer reworked with `success`/`failed` split and code 3 sentinel; `gen_response` helpers and `merge` for multi-step actions
- Short source codes with `SOURCES` mapping for request logging
- Player layer returns sentinels; `list` sorts songs by basename

## [0.2.0] - 2026-08-06

### Added

- SQLite persistence for library and playlists, sentinel singleton, backend shutdown cleanup
- `start` command and basic CLI frontend with `status` and transport controls
- Library: `lib.del`, `lib.list` with optional alias display
- Aliases: `lib.alias list/bind/unbind`
- Playlists: `lib.playlist create/list/add/open`
- `lib reset` with y/n confirmation
- Pytest suite for database and backend dispatch

### Changed

- Unified path resolution between frontend cwd and backend path joining

## [0.1.0] - 2026-07-31

### Added

- Initial project skeleton: backend-frontend architecture over socket IPC
- Length-prefixed JSON protocol (4-byte big-endian header) in `connection.py`
- Backend with unified command queue: socket requests and player events are serialized through a single dispatch loop
- Response template module (`response.py`) with declarative request validation via `ACTION_KEYS`
- Player module wrapping python-vlc: load, play, pause, resume, toggle, auto-next on track end
- platformdirs-based logging setup in `constants.py`
