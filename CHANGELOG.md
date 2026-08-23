# CHANGELOG

## [0.24.1] - 2026-08-23

### Changed

- Request validation refactored: `_request_verify` → `_process_request` — validation now also fills declared default values for absent optional keys, so action handlers read `request[key]` directly instead of `request.get(key, default)`. `ACTION_KEYS` entries are now `(type, is_required, default_value)` triples.
- Unknown keys (anything not in `ACTION_KEYS` nor `NON_ACTION_KEYS` — `action`/`cwd`/`source`) are logged as warnings instead of being silently ignored.
- `lib.meta.set` now declares all seven `METADATA` fields (`duration`, `bitrate`, `sample_rate`, `channels` joined the three string fields) with `None` defaults, so setting them over the protocol is type-checked (`int`); the CLI still only exposes `--name`/`--artist`/`--album`.

## [0.24.0] - 2026-08-23

### Added

- `lib add --loose-path` — allow adding songs whose path is not an existing file: any path that is format-valid is accepted, including directories and not-yet-existing files (useful for pre-registering songs before files arrive; `lib prune` later cleans up records whose files never show up). Format validation via the new `verify_path_format()` — rejects empty/NUL strings, and on Windows rejects illegal characters (`< > : " | ? *` outside the drive letter) and reserved device names (`CON`, `NUL`, `COM1`, …). Paths must still be format-valid; `lib.add` without the flag keeps rejecting missing files.
- `_add_song` now resolves relative paths against `cwd` (previously a relative path was checked against the daemon's own working directory, which could judge wrongly)
- `lib add` success responses are returned in the `attachment` (per-song add/meta/alias details) so the CLI can print them
- New `MissingCWD` response class: a cwd-missing error now says `requires a missing key of "cwd" because one or more paths provided are not absolute paths` instead of the generic missing-key message (used by `open`, `lib.info`, `lib.del`, `lib.scan`, `lib.meta.set`, `lib.alias.*`, `lib.add`)

### Fixed

- `_get_meta_from_file` crashed with `mutagen.MutagenError` when the path did not exist or was a directory (mutagen wraps the underlying `OSError`); it now catches `(OSError, mutagen.MutagenError)` and returns empty metadata, which `--loose-path` relies on

## [0.23.0] - 2026-08-23

### Added

- Songs can now be referenced by their library ID: any action that resolves a song (`open`, `lib.del`, `lib.playlist.add`/`lib.playlist.kick`, `lib.alias.list`/`lib.alias.bind`) accepts a numeric string like `123` and resolves it to the song with that ID. Lookup order is alias → song ID → path, so a numeric alias still wins and nonexistent IDs fall through to path lookup.

### Fixed

- The new song-ID branch used `str.isdigit()`, which accepts superscript (`²`) and circled (`①`) digits that `int()` cannot parse — a request like `open ²` crashed into a generic backend error. Switched to `isdecimal()`, whose accepted set matches `int()`.

## [0.22.0] - 2026-08-23

> **⚠️ Breaking Changes**
> - `lib.playlist.add` request key renamed: `song` → `songs` — now takes a list/tuple of strings (`IterType(str)`). The CLI argument order changed too: `lib playlist add <playlist> <song>...` (playlist first, then one or more songs).
> - `lib.playlist.kick` request key renamed: `song` → `songs` — same shape; the CLI is now `lib playlist kick <playlist> <song>...`.

### Added

- `lib playlist add <playlist> <song>...` — add multiple songs to a playlist in one request; per-song failures (song not in library, already in playlist) go to the `failed` list, message shows `songs added to playlist [ok/total]`
- `lib playlist kick <playlist> <song>...` — remove multiple songs from a playlist in one request; per-song failures go to the `failed` list, message shows `songs removed from playlist [ok/total]`
- New `BatchAuto` response class: builds the batch message with the success count (`[ok/total]`), picks the response code automatically (partial success = 0, all failed = 1) and forwards the `failed` list — now used by `lib.add`/`lib.del`/`lib.alias.bind`/`lib.alias.unbind`/`lib.playlist.add`/`lib.playlist.kick`

### Fixed

- `lib.playlist.kick` crashed with `UnboundLocalError` when the playlist did not exist (`song` was referenced outside the batch loop); now returns the normal `PlaylistNotExist` response
- Batch messages displayed the failure count (`[failed/total]`) instead of the success count — `BatchAuto` now reports `[ok/total]` like the pre-batch messages did
- Batch responses dropped their per-song failure details because the `failed=failed` argument was not forwarded at the call sites — all six batch actions now pass it through

## [0.21.0] - 2026-08-22

> **⚠️ Breaking Changes**
> - `lib.alias.bind` request key renamed: `alias` → `aliases` — now takes a list/tuple of strings (`IterType(str)`); the CLI takes multiple alias values after the song.
> - `lib.alias.unbind` request key renamed: `alias` → `aliases` — same shape; the CLI takes multiple aliases to unbind.

### Added

- `lib alias bind <song> <alias>...` — bind multiple aliases to one song in a single request; per-alias failures go to the `failed` list, message shows `bound [ok/total] aliases to <song>`
- `lib alias unbind <alias>...` — unbind multiple aliases in one request; missing aliases go to the `failed` list, message shows `unbound [ok/total] aliases`
- New `EmptyList` response class for "received empty list of X" failures (`lib.add`/`lib.del`/`lib.alias.bind`/`lib.alias.unbind` all use it)
- Request validation: optional `IterType` keys now accept an explicit `None` value (previously only the non-iterable branch did, so the CLI's `aliases=None` default failed `lib.add` validation)

### Fixed

- **Backend hang on any failed response** — `send_json` serialized the top-level `Response` with `dict()`, but `Response` objects nested inside the `failed` list were never converted, so `json.dumps` raised `TypeError: Object of type X is not JSON serializable`; that exception escaped `send_json` (only socket errors were caught) and killed the `_flush_buffer` consumer thread, leaving every later request stuck at "Received request". Now `json.dumps(..., default=...)` recursively converts nested `Response` objects, and the whole `_flush_buffer` handling loop is wrapped in `try/except` so no send error can ever kill the consumer thread again.
- `EmptyList` constructor was misspelled `__int__` (an `int()` hook, not an initializer), so `EmptyList('paths')` silently produced a response whose message was just `'paths'` — renamed to `__init__`
- Batch message wording: `successfully added`/`successfully removed` → `added`/`removed` (a failed response no longer claims success)

## [0.20.0] - 2026-08-22

> **⚠️ Breaking Changes**
> - `lib.del` request key renamed: `song` → `songs` — now takes a list/tuple of strings (`IterType(str)`); the CLI takes multiple positional songs.

### Added

- `lib del <song>...` — delete multiple songs in one request (each can be a path or alias)
- Batch delete reports per-song failures in the `failed` list (song not in library, etc.) and the message shows `successfully removed [ok/total] songs from library` — partial success is a success, all-failed is a failed response (same convention as `lib.add`/`lib.scan`)
- Deleting the currently-playing song still degrades it to a raw path and flips `in_library` to false, same as before

### Changed

- `lib.del` with an empty song list returns a failed response (`received empty list of songs`), matching `lib.add`'s empty-path behavior

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
