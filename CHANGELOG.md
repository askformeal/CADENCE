# CHANGELOG

## [Unreleased]

### Added

- `dice` command — switch to a random song in the current playlist
- `loop` command — toggle loop mode (replay the current song on end)

## [0.1.0] - 2026-07-31

### Added

- Initial project skeleton: backend-frontend architecture over socket IPC
- Length-prefixed JSON protocol (4-byte big-endian header) in `connection.py`
- Backend with unified command queue: socket requests and player events are serialized through a single dispatch loop
- Response template module (`response.py`) with declarative request validation via `ACTION_KEYS`
- Player module wrapping python-vlc: load, play, pause, resume, toggle, auto-next on track end
- platformdirs-based logging setup in `constants.py`
