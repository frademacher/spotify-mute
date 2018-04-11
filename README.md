# Spotify Mute

This Python script mutes your computer when Spotify starts playing advertisements. After the commercial break, your computer is unmuted again.

## Prerequisites
- OS: Spotify Mute only works for Linux distributions that include D-Bus (tested with Linux Mint 18.3).
- Supported Python version: 3 (tested with 3.5.2)
- Required Python modules possibly not included in Python distributions: PyGTK, pydbus
- Spotify needs to be started before running the script.

## Configuration
The script might be run by passing a configuration file with the `--config` argument. You need to specify the path to the configuration file via `--config={FULL_PATH_TO_CONFIGURATION_FILE}`. This file needs to be in the INI format (`#` is used for line comments). The main section is `[SPOTIFY_MUTE]`.

The following keys are required:
- `Mode`: Must currently exhibit the value `MUTIFY`.

The following keys are optional:
- `WaitBeforeUnmute`: Specifies the waiting time in seconds after which your computer gets unmuted again, when Spotify finished playing the current commercial break. *Valid values:* A floating point value greater or equal zero.
- `ShowNotification`: Specifies whether a notification shall be shown when the computer gets muted due the detection of the start of a commercial break. *Valid values:* Any string, but anything else other than `false` will be considered `true`. Note, that the key is not case sensitive, i.e., `False`, `falsE` or any other incarnation eventually evaluates to `false`.

In case no configuration file is passed, the keys have the following default values:
- `Mode: MUTIFY`
- `WaitBeforeUnmute: 0.0`
- `ShowNotification: true`

The repository also contains a sample configuration file called `sample_config.ini`.

## Starting the Script
1. Download or clone this repo.
2. Switch to the folder on your harddrive that contains the downloaded repo. Open a terminal.
3. Flag the script as being executable by typing `chmod u+x spotify_mute.py`.
4. Run the script with our without configuration file. Type either `./spotify_mute.py` or `./spotify_mute.py --config=={FULL_PATH_TO_CONFIGURATION_FILE}` in the terminal and hit return.
5. Lean back and continue to listen to Spotify.

If you want to stop the script, switch to the terminal that runs the script and hit Ctrl+C.
