# Configuration

CASCADE reads its options from a TOML file. The `config` commands that read and write it — `list`, `show`, `set`, `unset`, `open`, `path` and `gui`, plus `-d/--direct` — are listed in the [README](../README.md#configuration). The same options can be edited in a window instead — see the [configure GUI](../README.md#configure-gui).

## Config file

`%LOCALAPPDATA%\cascade\cascade\config.toml` on Windows (the location is platform-dependent, managed by `platformdirs`). `cascade config path` prints it, and `cascade config open` opens it in the system's default application, creating an empty file if there is none.

Options are grouped into TOML sections — `[network]`, `[service]`, `[playback]`, `[dash]`, `[appearance]`, `[lyric]` and `[config_gui]` — with `username` at the root of the file. `cascade config set` writes each option into its section for you.

## Options

| Option                                | Section                | Default                       | Description                                                                                            |
| ------------------------------------- | ---------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------ |
| `username`                          | *(root)*             | `J. Doe`                    | Name shown in the welcome message                                                                      |
| `backend_token`                     | `network`            | *(empty)*                   | Token the backend verifies requests with; empty disables auth                                          |
| `frontend_token`                    | `network`            | *(empty)*                   | Token frontends send with requests                                                                     |
| `backend_host` / `backend_port`   | `network`            | `127.0.0.1` / `17891`     | Address the backend listens on                                                                         |
| `frontend_host` / `frontend_port` | `network`            | `127.0.0.1` / `17891`     | Address the frontend sends requests to                                                                 |
| `connection_timeout`                | `network`            | `3`                         | Timeout of frontend waiting for the backend's acknowledge (seconds)                                    |
| `execution_timeout`                 | `network`            | `30`                        | Timeout of frontend waiting for the backend's response (seconds)                                       |
| `proxy`                             | `network`            | *(empty)*                   | Proxy used when fetching lyrics online; empty uses the system default                                  |
| `netease_skip_proxy`                | `network`            | `false`                     | Connect to the NetEase lyric source directly, ignoring`proxy`                                        |
| `hotkey`                            | `service`            | `true`                      | Start the hotkey frontend with the backend                                                             |
| `tray`                              | `service`            | `true`                      | Start the tray icon frontend with the backend                                                          |
| `lyric`                             | `service`            | `true`                      | Start the lyric board frontend with the backend                                                        |
| `engine`                            | `playback`           | `miniaudio`                 | Audio engine:`vlc` or `miniaudio` (see [Audio engines](../README.md#audio-engines))                 |
| `default_volume`                    | `playback`           | `100`                       | Volume on start (0~100)                                                                                |
| `default_shuffle`                   | `playback`           | `false`                     | Shuffle mode on start                                                                                  |
| `default_online_lyric`              | `playback`           | `false`                     | Use the online lyric source on start                                                                   |
| `pos_memorize_interval`             | `playback`           | `5`                         | Interval of memorized position updates (seconds)                                                       |
| `player_timeout`                    | `playback`           | `1`                         | Timeout of backend waiting for a player action (seconds)                                               |
| `dash_volume_step`                  | `dash`               | `5`                         | Volume increase/decrease step on the dashboard                                                         |
| `dash_pos_step`                     | `dash`               | `5`                         | Position forward/backward step on the dashboard                                                        |
| `escape_char`                       | `appearance`         | `true`                      | Use ANSI escape codes (colors) in the CLI and dashboard output                                         |
| `cli_box_style`                     | `appearance`         | `rounded`                   | Box style of the CLI                                                                                   |
| `dash_box_style`                    | `appearance`         | `rounded`                   | Box style of the dashboard                                                                             |
| `dash_poster_width`                 | `appearance`         | `80`                        | Width of the album cover in the dashboard's poster mode (columns)                                      |
| `dash_poster_height`                | `appearance`         | `64`                        | Height of the album cover in poster mode (pixels, 2 per terminal row)                                  |
| `dash_screen_buffer`                | `appearance`         | `true`                      | Use the terminal alt-screen buffer for the dashboard                                                   |
| `auto_dash_height`                  | `appearance`         | `true`                      | Size the dashboard height from the terminal height                                                     |
| `pause_hide_lyric`                  | `lyric`              | `true`                      | Hide the lyric board when playback is paused                                                           |
| `lyric_trans_bg`                    | `appearance`         | `false`                     | Use a fully transparent window background (keyed out) instead of an opaque backdrop on the lyric board |
| `lyric_hover_solid`                 | `appearance`         | `true`                      | Turn the lyric board fully opaque with a solid background when hovered (can be turned off)             |
| `lyric_height`                      | `appearance`         | `70`                        | Height of the lyric board (pixels)                                                                     |
| `lyric_x_offset`                    | `appearance`         | `0`                         | Horizontal offset of the lyric board from screen center (negative = left, positive = right)            |
| `lyric_font_family`                 | `appearance`         | *(empty → system default)* | Font family of the lyric board                                                                         |
| `lyric_font_size`                   | `appearance`         | `20`                        | Font size of the lyric board                                                                           |
| `lyric_font_bold`                   | `appearance`         | `false`                     | Use a bold font on the lyric board                                                                     |
| `lyric_font_color`                  | `appearance`         | `#797979`                   | Font color of the lyric board (hex)                                                                    |
| `lyric_bg_color`                    | `appearance`         | `#111111`                   | Solid background color of the lyric board shown on hover (hex)                                         |
| `lyric_opacity`                     | `appearance`         | `40`                        | Lyric board opacity when not hovered (0~100, 100 = fully opaque)                                       |
| `config_default_remote`               | `config_gui`           | `true`                        | Start the configure GUI in remote mode                                                                 |

The default value is used when an option is not set or the stored value is invalid. Most options take effect on the next backend start; the timeout / interval / step options are read live on every use, and `config_default_remote` on the next configure GUI start.
