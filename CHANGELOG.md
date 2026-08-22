# CHANGELOG

## [0.19.0] - 2026-08-22

> **⚠️ Breaking Changes**
> - `lib.add` request keys renamed: `path` → `paths`, `alias` → `aliases` — both now take a list/tuple of strings (`IterType(str)`); the CLI takes multiple positional paths and `-a/--aliases` takes multiple alias values.

### Added

- `lib add <path>...` — add multiple songs in one request; manual aliases via `-a/--aliases` bind positionally to the paths (count must match)
- Batch add reports per-song failures in the `failed` list (duplicate, invalid path, etc.) and the message shows `successfully added [ok/total] songs to library` — partial success is a success, all-failed is a failed response (same convention as `lib.info`)

### Changed

- `lib.scan` on a directory with no supported audio files now returns a success with a clear message (`No supported audio file found under <dir>`) instead of a self-contradicting `successfully added [0/0]` failed response
- `lib.scan` all-failed now returns a failed response with failures in the `failed` list (was success whenever the directory was non-empty)
- `lib.meta.set` message wording: `no metadata was given` → `no metadata was provided`

### Fixed

- `lib.add` `aliases` key in `ACTION_KEYS` had trailing spaces, silently disabling manual aliases

## [0.18.0] - 2026-08-21

### Added

- `lib info <song>...` — accept multiple songs at once; each missing song goes to the `failed` list instead of failing the whole request, and the message reports `got information of [ok/total] songs` (`0` successes still returns a failed response)
- `lib search <keyword>...` — multi-keyword search; by default all keywords must match (AND), `-o/--or` switches to any-keyword match (OR)
- `get_multi_song_aliases()` batch query so `lib search` fetches all aliases in one SQL call instead of one query per song

### Changed

- `lib.search` request key `keyword` now requires a list/tuple of strings (`IterType(str)`); the CLI takes `nargs='+'`
- `lib.scan` with a directory that contains no supported audio files is a success (`0/0`), matching the `lib.info` empty-list convention

### Fixed

- `lib.search` no longer matches `None` metadata fields (`str(None)` was searchable as `'none'`)
- `lib.scan` no longer references a `found` variable that belonged to `lib.prune` (`UnboundLocalError` when scanning an empty directory)

## [0.17.0] - 2026-08-21

### Added

- Request validation extracted into `_request_verify()` — dispatch now verifies all keys before running the action, and validation supports element types via `IterType(element_type)` so a key can require a list/tuple of a specific type (e.g. `(IterType(str), False)` means "optional list/tuple of strings")
- `InvalidKeyType` now reports the received type; new `InvalidElementType` response for mismatched elements inside a list/tuple
- `lib list -t/--show-tech` — show technical metadata (bitrate, sample rate, channels) in library listing
- `lib playlist list <name>` supports `-a` (aliases), `-p` (playlists), `-t` (tech metadata) like `lib list`

### Changed

- `lib info` and `lib list` share the same `_show_song_info()` renderer (was duplicated); `show_tech` controls technical metadata lines
- `sort_songs()` renamed to `_sort_songs()` (private); `_play_all()` now sorts songs by filename like playlists do
- Alias/playlist enrichment extracted into `_add_songs_aliases()` / `_add_songs_playlist_names()` helpers, reused by `lib.list` and `lib.playlist.list`

### Fixed

- `IterType` used a method named `self` and lacked `__init__`, so `IterType(str)` raised `TypeError` and chained calls returned `None` — replaced with a proper `__init__`
- `READABLE_TYPE_NAMES` lookup used the `IterType` instance as key while the dict stored the class, raising `KeyError` on validation failure — now looks up the class

## [0.16.0] - 2026-08-21

### Added

- Per-playlist playback position memory: `playlists` table gains a `last_num` column (migration), `_set_current_num()` writes the current song number into the active playlist, and reopening a playlist jumps back to the last played song (`_get_playlist_songs()` now also returns the playlist id)
- Play-all position memory: play-all sessions track their own `last_play_all_num` setting so `play-all` resumes where the previous all-songs session left off
- `current_song_num` is reset to 0 when loading a new list, but with `_set_current_num(0, update_database=False)` so initialization never overwrites a playlist's stored position

### Changed

- `current_song_open` renamed to `current_playlist`; `PLAY_ALL` sentinel marks an active play-all session
- `continue_last` no longer reads the global `last_num` setting — resume position now lives with the playlist (or play-all), so stale `last_num` values are ignored

### Fixed

- `get_playlist_last_num()` was missing `.fetchone()`, raising `TypeError: 'sqlite3.Cursor' object is not subscriptable` — now reads the row properly
- `set_playlist_last_num()` updated the wrong column (`SET num` instead of `SET last_num`), raising `no such column` — corrected
- `_get_playlist_songs()` returned `None` when `return_id=False`, breaking `lib playlist list <name>` — now falls through to `return result`
- `_play_all()` passed the raw string from `get_setting()` into `_switch_song()`, causing a `str`/`int` comparison error when resuming — now `int(last_num)`

## [0.15.0] - 2026-08-20

### Added

- `cadence reboot -c/--continue` — resume playback after rebooting the backend, same as `start -c`
- `play-all` now records `last_is_all` so `--continue` can resume an "all songs" session; `_play_all()` factored out and shared with `continue_last`

## [0.14.0] - 2026-08-20

### Added

- `cadence start -c/--continue` — resume the last opened song/playlist on backend startup (reads `last_song` / `last_num` / `last_cwd` settings); open action is now factored into `_open_song()` and reused by both paths
- `settings` table (key-value) in the database for persistent backend state; `last_song` stores the raw user input (alias/path/playlist name) so resume reproduces exactly how the song was opened
- `current_song_num` is persisted via `_set_current_num()` on every navigation (prev/next/switch/dice), so the resume position stays in sync
- `backend` source added to `SOURCES` for internal inter-process requests

## [0.13.0] - 2026-08-20

### Added

- `lib info <song> [-a] [-p]` — show detailed information of a single library song: name, artist, album, duration, bitrate, sample rate, channels, library ID, plus optional aliases (`-a`) and playlists (`-p`)
- Technical metadata now extracted and stored per song: `bitrate` (bps), `sample_rate`, `channels` — read from the audio file when adding songs (mutagen), displayed in `lib info` as kbps
- `SongOutput` class unifies how CLI renders song info (status / lib info / lib list); missing values display as `N/A` (file lacks it) vs `?` (backend did not provide it)
- Boxed output frames (`box()` + `wcwidth`) for status, lib info, and lib list — CJK-aware alignment
- Dependencies moved to pip-compile workflow: `requirements.in` (direct deps) compiles to `requirements.txt`; `requirements-dev.in` compiles to `requirements-dev.txt` (adds `pytest`, `bump-my-version`, `pip-tools`); `wcwidth` added as runtime dep

### Changed

- `status` attachment now uses `null` for unknown path/name/artist/album (was `'[path unknown]'` etc.) — CLI renders these as `?`/`N/A`
- `lib list` now also shows `Library ID` per song

## [0.12.0] - 2026-08-20

### Added

- Opening a song that is already in the current playlist now switches to it directly instead of reloading the whole list — playback position and current song index are preserved (`open` detects the path in `current_song_info` and calls `_switch_song`)

## [0.11.0] - 2026-08-20

### Changed

- Response system refactored from dict factories (`src/response.py`) to classes (`src/gen_response.py`): `Response` base + `Success` / `Failed` / `Dying` / `Undefined` / `UnknownAction` and typed failure subclasses
- Responses support `+` / `+=` / `append()` for merging (replacing `merge()`); `append()` preserves the caller's `attachment` / `failed` unless new values are explicitly given
- Invalid action message is now more specific: `unknown action received: "<action>"` instead of generic `invalid action`
- `[DEV]` prefix applied via attribute instead of dict access

## [0.10.1] - 2026-08-19

### Fixed

- Restart (`reboot`) no longer spams error logs with `[WinError 10054]` when the dying backend resets the connection mid-poll — `send_request` gained `expect_reset` (used by `test_alive`), silencing the expected reset in both `send_json` and `recv_json`
- `send_json` returns `False` on `ConnectionResetError` instead of implicitly falling through to `None`

## [0.10.0] - 2026-08-19

### Added

- `lib search` now also matches by filename (without extension), case-insensitive, after name/artist/album/alias
- `status` reports `playlist_len` (songs in current playlist) and `current_num` (0-based position); CLI shows `[current / total]`
- `status` reports `run_time` (backend uptime in seconds); CLI shows it formatted
- `prev` / `next` / `switch` / `dice` success messages include the resulting song's name

### Changed

- `format_ms` renamed to `format_time(raw_time, unit='ms'|'sec')` — one formatter for both milliseconds and seconds (uses `typing.Literal` for the unit parameter)
- Client socket `TIMEOUT` raised from 3s to 10s (slow `open` on network drives / large files)
- `current_song_num` is only synced after a successful `prev` / `next` / `switch` / `dice` — a failed switch no longer moves the reported current song

## [0.9.0] - 2026-08-19

### Added

- `lib prune` — delete all songs from the library whose file no longer exists on disk; `-d/--dry-run` shows what would be removed without deleting

### Changed

- `lib scan`'s `-p/--preview` renamed to `-d/--dry-run` (same behavior, standard naming)
- `merge` gained a `join_char` parameter (default `'|'`) so composite messages can join with a custom separator
- Backend refactor: `switch`, `jump`, and `stop` extracted into `_switch_song` / `_jump_to_pos` / `_stop_player` helpers; `_load_paths` gained a `jump_to_mem` flag; new `_remove_from_current` keeps the current playlist consistent when a song is pruned

## [0.8.2] - 2026-08-18

### Added

- `lib list --show-playlists` (`-p`) — show which playlists each song belongs to

### Fixed

- `lib reset` now resets `user_version` so the database is properly rebuilt
- Corrected log message in `get_playlists_info` (was printing builtin `id`)

## [0.8.1] - 2026-08-18

### Added

- `lib search <keyword>` — search songs in library by name/artist/album/alias (case-insensitive)

### Changed

- `restart` renamed to `replay` (clear memorized progress and replay the current song) — no longer confused with `reboot`

## [0.8.0] - 2026-08-18

### Added

- Duration metadata — auto-extracted from audio files, stored in the library, shown in `lib list`
- Database migration system — `user_version`-based, idempotent schema upgrades on startup

### Changed

- Status `unknown` placeholders now use `[brackets]` (e.g. `[path unknown]`)
- `format_ms(None)` returns `--:--:--` instead of crashing

## [0.7.0] - 2026-08-18

### Added

- `seek` command — jump to a specific time (`HH:MM:SS`)

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
