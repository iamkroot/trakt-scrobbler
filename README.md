# Trakt Scrobbler

A trakt.tv scrobbler for your computer.

## What is Trakt?

Automatically scrobble TV show episodes and movies you are watching to [Trakt.tv](https://trakt.tv)! It keeps a history of everything you've watched!

## What is trakt-scrobbler?

Trakt.tv has a lot of [plugins](https://trakt.tv/apps) to automatically scrobble the movies and episodes you watch from your media center. But there is a dearth of up-to-date apps for syncing your progress on Desktop environments. This is where `trakt-scrobbler` comes in! It is a Python application that runs in the background and monitors your media players for any new activity. When it detects some file being played, it determines the media info (such as name of the movie/show, episode number, etc.) and sends this to trakt servers, so that it can be marked as "Currently Watching" on your profile. No manual intervention required!

## Features

* Uses [guessit](https://github.com/guessit-io/guessit) to extract media information from its file path. For cases when it misidentifies the files, you can specify a regex to manually extract the necessary details.
* Scrobbling is independent of the player(s) where the media is played. Support for new players can thus be easily added.
* Currently has support for:
    * [VLC](https://www.videolan.org/vlc/) (via web interface)
    * [Plex](https://www.plex.tv) (doesn't require Plex Pass)
    * [MPV](https://mpv.io) (via IPC server)
    * [MPC-BE](https://sourceforge.net/projects/mpcbe/)/[MPC-HC](https://mpc-hc.org) (via web interface).
* **Folder whitelisting:** Only media files from subdirectories of these folders are synced with trakt.

For more information, see the [`How it works`](#how-it-works) section.

## Getting started

### Setting up

#### Players

* **VLC:** Enable the Lua Web Interface from advanced options. Don't forget to specify the password in Lua options.

    ![VLC Web Interface](https://wiki.videolan.org/images/thumb/VLC_2.0_Activate_HTTP.png/450px-VLC_2.0_Activate_HTTP.png)

* **Plex:** No server side set up is required, as the app uses the existing API. Do note that since this is a polling based approach, it will be inferior to Webhooks. So if you are a premium user of Plex, it is recommended to use that directly. This app is mainly useful for those users who don't need most of the features of Plex Pass.

* **MPV:** Enable the [JSON IPC](https://mpv.io/manual/master/#json-ipc), either via the mpv.conf file, or by passing it as a command line option.

* **MPC-BE/MPC-HC:** Enable the web interface from Options.

#### Configuration

The config is stored in [TOML](https://github.com/toml-lang/toml) format. After editing, please use [this](http://toml-online-parser.ovonick.com/) website to validate the file. See the [Sample Config](sample_config.toml).

* `fileinfo.whitelist`: (List of folder path strings | Default: `[]` aka Allow all)
    * List of directories you want to be scanned for shows or movies.
    * If empty, all files played in the player are scanned.
    * You can prevent the program from scanning all played files if your shows and movies are located in fixed directories.
    * If possible you should use this option to minimize traffic on the Trakt API.
* `fileinfo.include_regexes`: (Default: `{movie = [], episode = []}`)
    * If you find that the default module for identifying media info ([guessit](https://github.com/guessit-io/guessit)) is misidentifying some titles, you can specify the regex for that file path.
    * The regex should have posix-like path, and not Windows' `\` to separate directories.
    * The minimum required information is the title of the file, and episode number in the case of TV Shows. If season is not found, it defaults to 1.
    * Mainly useful for Anime since they don't follow the season convention.
* `players.monitored`: (List of player names)
  Specify players which are to be monitored for scrobbling. (Ensure that if both MPCHC and MPCBE are to be monitored, then their ports should be different)
* Other player specific parameters: See sample config for the required attributes.

### Installation

1. Clone the repo to a directory of your choice/click "[Download as zip](https://github.com/iamkroot/trakt-scrobbler/archive/master.zip)" and extract it.
2. Rename the `sample_config.toml` to `config.toml` and set the required values (See [Configuration](#Configuration) section).
3. Ensure you have [Python 3.6](https://www.python.org/downloads/) or higher installed, and in your system `PATH`.
4. Open a terminal/command prompt.
5. Navigate to the directory from Step 1. (Using `cd` command)
6. Run `cd tools`
7. Run `python3 install.py` (or `python install.py` if that fails). This will complete all the steps for installation. You will be prompted to authorize the program to access the Trakt.tv API. Follow the steps on screen to finish the process. In the future, the script will run on computer boot, without any need for human intervention.

**For Linux:**
To enable notification support on Linux, `libnotify` needs to be installed (Reboot after installation).
* Arch/Manjaro: `pacman -S libnotify`
* Ubuntu: `apt install libnotify-bin`

## FAQs

#### It doesn't work. What do I do?

First, look through the [log file](#where-is-the-log-fileother-data-stored) to see what went wrong. If you are unable to fix the problem, feel free to create an [Issue](https://github.com/iamkroot/trakt-scrobbler/issues).

#### How to stop the running app?

* **Linux:** `systemctl --user stop trakt-srobbler`
* **Mac:** `launchctl unload ~/Library/LaunchAgents/trakt_scrobbler.plist`
* **Windows:** Terminate `pythonw.exe` from task manager

#### How to update?

1. Stop the app using instructions above.
2. Follow the steps given in [Installation section](#installation)

#### How to edit config after installation?

Location for config file:

* **Linux:** `~/.config/trakt-scrobbler/config.toml`
* **Mac:** `~/Library/Application Support/trakt-scrobbler/config.toml`
* **Windows:** `C:\Users\<your name>\AppData\Roaming\trakt-scrobbler\config.toml` (Shortcut: `%APPDATA%\trakt-scrobbler`)

After editing, reboot your PC for the changes to take effect.

#### Where is the log file/other data stored?

* **Linux:** `~/.local/share/trakt-scrobbler/`
* **Mac:** Same as config file (see above)
* **Windows:** Same as config file (see above)

The latest log is stored in a file named `trakt_scrobbler.log`; older logs can be found in the files `...log.1`, `...log.2`, and so on.
Everything is in human readable form, so that you can figure out what data is used by the app. While submitting a bug report, be sure to include the log file contents.

## How it works

This is an application written in the Python programming language, designed for hassle-free integration of your media players with Trakt. Once set up, you can forget that it exists.

* The app is designed to start with your PC, and remain running in the backgroud.
* It has a "monitor" for each media player you specify. This monitor keeps checking if the media player is running or not. If not, you get the "Could not connect..." message in the log file.
* When the player is running, the monitor extracts the currently playing media information from the player.
* This media file path is parsed using `guessit` (or regexes, if specified) to recognize the metadata such as "Title", "Season", etc.
* This info, along with the playing state (`playing`, `stopped` or `paused`) and progress are then sent to trakt.tv using their API to update their side and mark the media as "Currently Watching", "Finished", etc and you get a notification of the same.
* Once the player is closed, the monitor goes back to "dormant" state, where it waits for the player to start again.

### Other details
* The checking for media info from player happens at a set interval (`poll_interval` in config, 10 secs by default), which is the maximum delay between you starting/stopping/pausing the player, and the monitor recognizing that activity.
* Generally, this app provides "live" updates to trakt regarding your playing status. However, in cases where the internet is down, when you finish playback, the app remembers the media that you have finished watching (progress > 90%) and will try to sync that information with trakt the next time internet becomes available.

## TODO

* [x] Switch to poetry for dependency management
* [x] Make a unified installer script for all OSes
* [ ] Proper configuration management module with autodetection for players
* [ ] A CLI command for controlling the app (start, stop, list recents, config, etc.)

## Contributing

Feel free to create a new issue in case you find a bug/want to have a feature added. Proper PRs are welcome.

## Authors

* [iamkroot](https://www.github.com/iamkroot)

## Acknowledgements

* Inspired from [TraktForVLC](https://github.com/XaF/TraktForVLC)
* [mpv-trakt-sync-daemon](https://github.com/stareInTheAir/mpv-trakt-sync-daemon) was a huge help in making the mpv monitor
