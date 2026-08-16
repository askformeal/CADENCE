# CADENCE

**C**ommand-line **A**udio **D**ecoding **E**ngine with **N**avigation and **C**ontinuous **E**xecution

Retrieves collections of mechanically-represented wave data from persistent storage, decompartmentalizes their format-specific encapsulation, reconstitutes the original waveform through algorithmic reconstruction, and transmits the resulting signal to a computer-connected mechanical wave generator. Controlled via a teletype-like interactive interface. Supports automatic transition to the next data set or the beginning of the current data set upon completion, based on a configured mode.

(CLI music player. Lives in the terminal.)

## Logs

Log file location (platform-dependent, managed by platformdirs):

| Platform | Path                                                                                                |
| -------- | --------------------------------------------------------------------------------------------------- |
| Windows  | `%LOCALAPPDATA%\cadence\cadence\Logs\cadence.log`                                                 |
| Linux    | `$XDG_STATE_HOME/cadence/log/cadence.log`, defaults to `~/.local/state/cadence/log/cadence.log` |
| macOS    | `~/Library/Logs/cadence/cadence.log`                                                              |

## License

MIT License, because using it is your loss.
