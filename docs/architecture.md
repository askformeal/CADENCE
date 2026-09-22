# Architecture

CASCADE is a backend daemon plus thin frontends that talk to it over a local socket; the wire protocol is documented in [protocol.md](protocol.md).

- **Backend** (`src/backend/`) — owns the audio engine (`playback/`: `base_engine.py` declares the `BaseEngine` ABC, `engine_mixin.py` holds the engine flow shared by both implementations as a mixin, and `vlc_engine.py` / `mini_engine.py` implement the decoding, selected by the `engine` config option; session state, lyrics and cover art live in their own mixins) and the SQLite database (`database/`, split into per-domain mixins), listens on `127.0.0.1:17891` for JSON requests over a socket. Action handlers live in `handlers/` and dispatch through a `ROUTER` table keyed by action name; playback state is held in the `Playback` class and injected into handlers via a `Context`.
- **Frontends** (`src/frontend/`) — `cli/` (the `cascade` CLI), `hotkey.py` (media key hotkeys), `tray.py` (system tray icon), `dash/` (interactive dashboard), `lyric.py` (floating lyric board), `config_gui/` (configure GUI window). They send action requests to the backend and format responses. All frontends share `client.py` and `song_output.py`.
