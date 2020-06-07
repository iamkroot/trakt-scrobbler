# Trakt Scrobbler

A trakt.tv scrobbler for your computer.

## What is Trakt?

Automatically scrobble TV show episodes and movies you are watching to [Trakt.tv](https://trakt.tv)! It keeps a history of everything you've watched!

## What is trakt-scrobbler?

Trakt.tv has a lot of [plugins](https://trakt.tv/apps) to automatically scrobble the movies and episodes you watch from your media center. But there is a dearth of up-to-date apps for syncing your progress on Desktop environments. This is where `trakt-scrobbler` comes in! It is a Python application that runs in the background and monitors your media players for any new activity. When it detects some file being played, it determines the media info (such as name of the movie/show, episode number, etc.) and sends this to trakt servers, so that it can be marked as "Currently Watching" on your profile. No manual intervention required!

## Features

*   Full featured command line interface to control the service. Just run `trakts`.
*   Automatic media info extraction using [guessit](https://github.com/guessit-io/guessit).
*   Scrobbling is independent of the player(s) where the media is played. Support for new players can thus be easily added.
*   Currently supports:
    *   [VLC](https://www.videolan.org/vlc/) (via web interface)
    *   [Plex](https://www.plex.tv) (doesn't require Plex Pass)
    *   [MPV](https://mpv.io) (via IPC server)
    *   [MPC-BE](https://sourceforge.net/projects/mpcbe/)/[MPC-HC](https://mpc-hc.org) (via web interface).
*   **Folder whitelisting:** Only media files from subdirectories of these folders are synced with trakt.
*   Optionally, you can receive a quick notification that the media start/pause/stop activity has been scrobbled.
*   For cases when it misidentifies the files, you can specify a regex to manually extract the necessary details.
*   Proxy support: Optionally specify a proxy server to handle all communication with trakt servers!

For more information, see the [`How it works`](#how-it-works) section.

## Getting started

### Players

*   **VLC:** Enable the Lua Web Interface from advanced options. Don't forget to specify the password in Lua options.

      ![VLC Web Interface](https://wiki.videolan.org/images/thumb/VLC_2.0_Activate_HTTP.png/450px-VLC_2.0_Activate_HTTP.png)

*   **Plex:** No server side set up is required, as the app uses the existing API. Do note that since this is a polling based approach, it will be inferior to Webhooks. So if you are a premium user of Plex, it is recommended to use that directly. This app is mainly useful for those users who don't need most of the features of Plex Pass.

*   **MPV:** Enable the [JSON IPC](https://mpv.io/manual/master/#json-ipc), **either** via .conf file or as a command line option:
    *   **mpv.conf** (Recommended): Add `input-ipc-server=<path>` to the top of the [`mpv.conf` file](https://mpv.io/manual/master/#configuration-files). (Linux: `~/.config/mpv/mpv.conf`, Windows: `C:\users\<USERNAME>\AppData\Roaming\mpv\mpv.conf`)
    *   **Command line** (If you are using a wrapper over mpv): `mpv file.mkv --input-ipc-server=/tmp/mpvsocket` (linux) and `mpv file.mkv --input-ipc-server=\\.\pipe\mpvsocket` (windows). Note that in this case, the scrobbler won't be able to autodetect the path, so you need to manually add that using `trakts config set players.mpv.ipc_path <PATH>`

*   **MPC-BE/MPC-HC:** Enable the web interface from Options.

### Installation
(For updating, see [FAQ section](#how-to-update))  
For Arch (and its derivatives) users: An AUR package exists at [trakt-scrobbler](https://aur.archlinux.org/packages/trakt-scrobbler/), thanks to [@ahmubashshir](https://github.com/ahmubashshir).

**Windows/Mac/Linux installation steps:**
1.  Open a terminal/powershell.
2.  Ensure you have [Python 3.7](https://www.python.org/downloads/) or higher installed, and in your system `PATH`. (Check by running `python --version`)
3.  Ensure `pip` is installed. (Check: `pip --version`)
4.  Install [`pipx`](https://pipxproject.github.io/pipx/):  
    MacOS:
    ```bash
    brew install pipx
    pipx ensurepath
    ```
    Linux and windows (replace `python3` with `python` if the commands fail):
    ```bash
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    ```
    (Windows users may require a reboot after this step)
5.  Run `pipx install trakt-scrobbler`. You will now have the `trakts` command available.  
For SOCKS proxy support, use `pipx install "trakt-scrobbler[socks]"`.
6.  Run `trakts init`. You will be prompted to select the players to be monitored, and authorize the app to access the Trakt.tv API on your behalf. Follow the steps on screen to finish the process.

**For Linux:**
To enable notification support on Linux, `libnotify` needs to be installed (Reboot after installation).

*   Arch/Manjaro: `pacman -S libnotify`
*   Ubuntu: `apt install libnotify-bin`

## `trakts` command usage:

All commands have descriptive help messages available. So in case of doubt, simply add `--help` to the (sub)command to see the help docs (Example: `trakts autostart --help` and `trakts --help`). For reference, the various available commands are:

*   `auth`: Shows the status of the trakt authentication. If no token is found, or if the token in expired, it runs the authetication flow for trakt.tv  
    You can pass `--force` option to make it ignore the existing token, and force the authentication again.

*   `autostart`: Controls the autostart behaviour of the scrobbler

*   `backlog`: Manage the backlog of watched media yet to be synced with trakt servers (mostly due to internet connectivity issues). Read [this](#backlog-cleaner) for more info

    *   `list`: Lists all the files in the backlog

    *   `clear`: Try to add the unsynced files to trakt history

*   `config`: Edits the scrobbler config settings. See [Configuration](#configuration) section for more details

    *   `list`: This command will list the parameters in the config, along with their current values.
          Eg: `trakts config list`

            players.monitored = ['mpv', 'vlc']
            players.skip_interval = 5
            general.enable_notifs = True
            fileinfo.whitelist = ['/path/to/movies', '/path/to/anime', '/path/to/TV']

          Additionally, it also accepts a `--all` option, which can be used to list *ALL* the config parameters, including those not overriden by the user.

    *   `set`: Set the value for a config parameter.

        *   Separate multiple values with spaces. 
              Eg: `trakts config set players.monitored mpv vlc mpc-be`

                User config updated with 'players.monitored = ['mpv', 'vlc', 'mpc-be']'

        *   For values containing space(s), surround them with double-quotes. 
              Eg: `trakts config set fileinfo.whitelist D:\Media\Movies "C:\Users\My Name\Shows"`

                User config updated with 'fileinfo.whitelist = ['D:\\Media\\Movies', 'C:\\Users\\My Name\\Shows']'

        *   Use `--add` to avoid overwriting the previous list values (whitelist, monitored, etc.):  
              `trakts config set players.monitored mpv vlc`  
              `trakts config set --add players.monitored plex mpc-hc`  
              will have final value: 

                User config updated with 'players.monitored = ['mpv', 'vlc', 'plex', 'mpc-hc']'
    *   `unset`: Reset a config value to its default.

*   `init`: Runs the initial setup of the scrobbler.
*   `log`: Access the log file, mainly for debugging purposes.  
    Subcommands: (Run as `trakts log <subcommand>`)
    *   `open`: Opens the latest log file in your default editor.
    *   `path`: Prints the location of the log file.
*   `plex`: Command to run the auth flow for Plex.
    You can pass `--force` option to make it ignore the existing token, and force the authentication again.
*   `run`: Run the scrobbler in the foreground. Mainly needed in case you have disabled the autostart service, and want to run the app manually.
*   `start`: Starts the trakt-scrobbler service. If already running, does nothing.
    *   Use `--restart` to force restart the service.
*   `status`: Shows the status trakt-scrobbler service.
*   `stop`: Stops the trakt-scrobbler service.
*   `whitelist`: Shortcut command to add folder(s) to whitelist in config.
    *   `add`: Add folder(s) to whitelist.  
           Eg: `trakts whitelist add D:\Media\Movies "C:\Users\My Name\Shows"`  
        *For folders containing spaces, use double quotes*

    *   `show`: List the current folders in whitelist.
    *   `remove`: Interactively remove folder(s) from whitelist.

## FAQs

#### It doesn't work. What do I do?

First, look through the log file (using the `trakts log` command) to see what went wrong. If you are unable to fix the problem, feel free to create an [Issue](https://github.com/iamkroot/trakt-scrobbler/issues).

#### How to update?

1.  Stop the app using `trakts stop`
2.  Run `pipx upgrade trakt-scrobbler`
3.  Start the app again using `trakts start`

#### How to update from pre 1.0.0 versions?

There has been a major UX overhaul with v1.0.0, due to the introduction of the `trakts` command, changes in how config is stored and a much simpler way of installation. So long story short, you will have to remove the older version and re-install using the [new method](#installation). In some cases, you may also have to set some configuration parameters again, if you have custom overrides - use `trakts config` command for that.

**Old version uninstall steps:**  
In a terminal/command prompt, run the following commands:
*   **Linux**
    1.  `systemctl --user stop trakt-scrobbler` to stop the background service.
    2.  `cd ~/.local/trakt-scrobbler/ && poetry env remove python3` to remove python environment.
    3.  `cd ~ && rm -rf ~/.local/trakt-scrobbler` to remove installed code files.
*   **MacOS**
    1.  `launchctl stop com.github.iamkroot.trakt-scrobbler` to stop the background service.
    2.  `cd ~/Library/trakt-scrobbler && poetry env remove python3` to remove python environment.
    3.  `cd ~ && rm -rf ~/Library/trakt-scrobbler` to remove installed code files.
*   **Windows**
    1.  `taskkill /im pythonw.exe` to stop the background service.
    2.  `del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\trakt-scrobbler.bat"` to delete the autostart script.
    3.  `cd "%LOCALAPPDATA%\trakt-scrobbler"`
    4.  `poetry env remove python3` to remove python environment.
    5.  `cd %LOCALAPPDATA%`
    5.  `rd /S /Q "%LOCALAPPDATA%\trakt-scrobbler"` to remove installed code files.

You should also uninstall poetry if you don't require it:
*   `osx / linux / bashonwindows`: `POETRY_UNINSTALL=1 curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python`
*   `windows powershell`: `$env:POETRY_UNINSTALL = 1; (Invoke-WebRequest -Uri https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py -UseBasicParsing).Content | python`

After this, you can install the new version using steps in [Installation](#installation) section.

#### Where is the log file/other data stored?

*   **Linux:** `~/.local/share/trakt-scrobbler/`
*   **Mac:** `~/Library/Application Support/trakt-scrobbler/`
*   **Windows:** `%APPDATA%\trakt-scrobbler\`

The latest log is stored in a file named `trakt_scrobbler.log`; older logs can be found in the files `...log.1`, `...log.2`, and so on.
Everything is in human readable form, so that you can figure out what data is used by the app. While submitting a bug report, be sure to include the log file contents.

## How it works

This is an application written in the Python programming language, designed for hassle-free integration of your media players with Trakt. Once set up, you can forget that it exists.

*   The app is designed to start with your PC, and remain running in the backgroud.
*   It has a "monitor" for each media player you specify. This monitor keeps checking if the media player is running or not. If not, you get the "Could not connect..." message in the log file.
*   When the player is running, the monitor extracts the currently playing media information from the player.
*   This media file path is parsed using `guessit` (or regexes, if specified) to recognize the metadata such as "Title", "Season", etc. (See: [Identifying Media](#identifying-media))
*   This info, along with the playing state (`playing`, `stopped` or `paused`) and progress are then sent to trakt.tv using their API to update their side and mark the media as "Currently Watching", "Finished", etc and you get a notification of the same.
*   Once the player is closed, the monitor goes back to "dormant" state, where it waits for the player to start again.

### Other details

#### Polling for activity

The checking for media info from player happens at a set interval (`poll_interval` in config, 10 secs by default), which is the maximum delay between you starting/stopping/pausing the player, and the monitor recognizing that activity.

#### Identifying media

Here's a brief overview of how the scrobbler identifies the movie/show:
1. It uses the file path of the media being played and extracts the title, season, ep, year, etc. using some heuristics. Note that this is very much prone to errors, so make sure your media directories are organized and named properly.
2. Next, just like you would in real life, the app uses Trakt search to find the corresponding show/movie in the trakt servers. The search is mainly done on the info extracted from step 1: the title, the type (movie or show), and year (if available). It picks the topmost result that trakt gives, since that has the highest score and matches our given info the most. Again, this is prone to errors, since the trakt search result might not be the actual movie/show being played.
3. This returned trakt result (as a numeric ID) is stored on your PC, and every time you play the same movie/show, this numeric id is used to identify the media on trakt servers. This means that the search happens only for the first time a movie/show is played.

#### Backlog Cleaner

Generally, this app provides "live" updates to trakt regarding your playing status. However, it may happen that the app is unable to communicate with trakt servers (probably due to connection issues), and thus scrobbling updates won't be meaningful. For such cases, the app maintains a "backlog cleaner" which remembers the media that you have finished watching (progress > 80%) and will try to sync that information with trakt the next time its servers are reachable.

## Configuration

*   The config is stored in [YAML](https://yaml.org) format.

*   Most parameters have default values, stored in [`config_default.yaml`](trakt_scrobbler/config_default.yaml). 

*   The file is hierarchical, with multiple sections such as `general`, `players`, etc.

*   Everything you see on the left hand side of a `:` is a *key*. This means `players` is a key, `vlc` is a key, and so is `poll_interval`.

*   You can use the `config` command to override the values easily. (See [Commands Reference](#trakts-command-usage))

*   To access a config parameter, use the dotted-notation - use a `.` to go down a hierarchy level.  
    Example: `players.vlc.poll_interval` selects what you think it selects :P  
    (The `_` is not special, it's just a way for programmers to represent spaces in names)

### Reference
*   `general`
    *   `enable_notifs`: (Default: `true`) Enable notifications after successful scrobbles.
    *   `proxies`: (Default: `{}`)
        *   Defines the proxies to be used for external connections.
        *   See [this](https://requests.readthedocs.io/en/latest/user/advanced/#proxies) for format.
        *   Example command: `trakts config set general.proxies.https "socks5://my-proxy.example.com:1234"`  
            This adds a `SOCKSv5` proxy for the `HTTPS` protocol, and is identical to setting `proxies = {'https': 'socks5://my-proxy.example.com:1234'}` in the Python `requests` library, or in `YML` form:
            ```yml
            proxies:
                https: socks5://my-proxy.example.com:1234
            ```
*   `fileinfo`:
    *   `whitelist`: (List of folder path strings | Default: `[]` aka Allow all)
        *   List of directories you want to be scanned for shows or movies.
        *   If empty, all files played in the player are scanned.
        *   You can prevent the program from scanning all played files if your shows and movies are located in fixed directories.
        *   If possible you should use this option to minimize traffic on the Trakt API.
    *   `include_regexes`: (Default: `{movie = [], episode = []}`)
        *   If you find that the default module for identifying media info ([guessit](https://github.com/guessit-io/guessit)) is misidentifying some titles, you can specify the regex for that file path.
        *   The regex should have posix-like path, and not Windows' `\` to separate directories.
        *   The minimum required information is the title of the file, and episode number in the case of TV Shows. If season is not found, it defaults to 1.
        *   Example command: `trakts config set --add fileinfo.include_regexes.episode ".*/(?P<title>.+?)(\s\[[0-9]{3,4}p\])?/(?P<episode>\d+) - (?:.*)"`  
            This adds a new regex string (everything between the `"`) to the list of episode regexes, which can be used to extract info from Anime episodes of the form `Name of anime [720p]/12 - episode name.mkv`
        *   If season is not provided, it will default to `1`. This is mainly useful for anime since they don't follow the SxxExx format and fail to be recognized by the default parser. 
*   `players`:
    *   `monitored`: (List of player names | Default: `[]`) Specify players which are to be monitored for scrobbling.
    *   `skip_interval`: (Default: `5`) Min percent jump to consider for scrobbling to trakt. Useful when you skip ahead a few seconds, and don't want to spam the trakt API.
    *   Other player specific parameters: For most installations, you won't have to fiddle with these as the app can automatically read the settings of the players and extract the necessary values.
*   `backlog`:
    *   `clear_interval`: (Default: `1800` i.e., 30 minutes) How often the app should try to sync previously failed scrobbles with trakt.
    *   `expiry`: (Default: `2592000` i.e., 30 days) The maximum time an item can remain in the backlog.

## TODO

*   [x] Switch to poetry for dependency management
*   [x] Make a unified installer script for all OSes
*   [x] Proper configuration management module with autodetection for players
*   [x] A CLI for controlling the app (start, stop, config, etc.)
*   [ ] Use a proper [Windows Service](http://thepythoncorner.com/dev/how-to-create-a-windows-service-in-python/) instead of an autostart script

## Contributing

Feel free to create a new issue in case you find a bug/want to have a feature added. Proper PRs are welcome.

## Authors

*   [iamkroot](https://www.github.com/iamkroot)

## Acknowledgements

*   Inspired from [TraktForVLC](https://github.com/XaF/TraktForVLC)
*   [mpv-trakt-sync-daemon](https://github.com/stareInTheAir/mpv-trakt-sync-daemon) was a huge help in making the mpv monitor
