# Trakt Scrobbler
A trakt.tv scrobbler for your computer.

## What is Trakt?
Automatically scrobble TV show episodes and movies you are watching to [Trakt.tv](https://trakt.tv)! It keeps a history of everything you've watched!

## What is trakt-scrobbler?
Trakt.tv has a lot of [plugins](https://trakt.tv/apps) to automatically scrobble the movies and episodes you watch from your media center. But there is a dearth of up-to-date apps for syncing your progress on Desktop environments. This is where `trakt-scrobbler` comes in! Built using Python, it supports all major OS platforms (Linux, Mac and Windows), as well as all major media players.

## Features
+ Uses [guessit](https://github.com/guessit-io/guessit) to extract media information from its file path. For cases when it misidentifies the files, you can specify a regex to manually extract the necessary details.
+ Scrobbling is independent of the player(s) where the media is played. Support for new players can thus be easily added.
+ Currently has support for:
	+ [VLC](https://www.videolan.org/vlc/) (via web interface)
	+ [MPV](https://mpv.io) (via IPC server)
	+ [MPC-BE](https://sourceforge.net/projects/mpcbe/) (via web interface).
	+ [MPC-HC](https://mpc-hc.org) (via web interface).

## Getting started
### Setting up
#### Players
+ VLC: Enable the Lua Web Interface from advanced options. Don't forget to specify the password in Lua options.

	![VLC Web Interface](https://wiki.videolan.org/images/thumb/VLC_2.0_Activate_HTTP.png/450px-VLC_2.0_Activate_HTTP.png)

+ MPV: Enable the [JSON IPC](https://mpv.io/manual/master/#json-ipc), either via the mpv.conf file, or by passing it as a command line option.

+ MPC-BE/MPC-HC: Enable the web interface from Options.

#### Configuration
The config is stored in [TOML](https://github.com/toml-lang/toml) format. After editing, please use [this](http://toml-online-parser.ovonick.com/) website to validate the file. 

Parameter | Explanation |
--------- | -----------
`fileinfo.whitelist`| List of strings \| Default: `[]` <br> List of directories you want to be scanned for shows or movies. If empty, all files played in the player are scanned. You can prevent the program from scanning all played files if your shows and movies are located in fixed directories. If possible you should use this option to minimize traffic on the Trakt API.
`fileinfo.include_regexes`| Dict of list of strings \| Default: `{}` <br> If you find that the default module for identifying media info ([guessit](https://github.com/guessit-io/guessit)) is misidentifying some titles, you can specify the regex for that file path. <br> The regex should have posix-like path, and not Windows' `\` to separate directories. <br>The minimum required information is the title of the file, and episode number in the case of TV Shows. If season is not found, it defaults to 1.
`players.monitored`| List of strings <br> Specify players which are to be monitored for scrobbling. (Ensure that if both MPCHC and MPCBE are to be monitored, then their ports should be different.)
Other player specific parameters| See sample config for the required attributes.

### Installation
1. Clone the repo to a directory of your choice/click "[Download as zip](https://github.com/iamkroot/trakt-scrobbler/archive/master.zip)" and extract it.
2. Rename the `sample_config.toml` to `config.toml` and set the required values (See [Configuration](#Configuration) section). 
3. Ensure you have [Python 3.6](https://www.python.org/downloads/) or higher installed, and in your system `PATH`.
4. Depending on your OS, proceed as follows: 
	+ **Linux**<br>
		At the root of cloned project directory, run `scripts/linux-install-service.sh`. This will copy the files to `~/.local/trakt-scrobbler`, create the virtualenv, enable the startup service and finish device authentication with trakt.

	+ **Windows**<br>
		At the root of cloned project directory, run `scripts\windows-install.bat`. This will copy the files to `%LOCALAPPDATA%\trakt-scrobbler` directory, create the virtualenv, enable the startup service and finish device authentication with trakt.

	+ **MacOS**<br>
		I will try to make a install script for Mac soon. Till then, here are the manual steps you can follow:
		1. Inside the project directory root, run `pipenv install`. This will create a virtualenv, and install the necessary requirements.
		2. Run `pipenv --py` to find the location of python interpreter of virtualenv. 
		3. Edit the `scripts/trakt_scrobbler.plist` file to add the correct folder path of the project.
		4. `cp scripts/trakt_scrobbler.plist ~/Library/LaunchAgents/`
		5. `launchctl load ~/Library/LaunchAgents/trakt_scrobbler.plist`
		6. Type `pipenv run python main.py` to start the program. You will be prompted to authorize the program to access the Trakt.tv API. Follow the steps on screen to finish the process. In the future, the script will run on computer boot, without any need for human intervention.

5. To enable notification support on Linux/MacOS, the dbus libraries need to be installed (Reboot after installation).
	- Ubuntu: `apt install python3-dbus`
	- MacOS: `brew install dbus`

## Updating
1. Kill the app.
	- Linux: `systemctl --user stop trakt-srobbler`
	- Mac: `launchctl unload ~/Library/LaunchAgents/trakt_scrobbler.plist`
	- Windows: Kill `pythonw.exe` from task manager
2. Open terminal in old installation directory and run `pipenv --rm` then close the terminal and remove the directory.
	- Linux: `~/.local/trakt-scrobbler`
	- Mac: Depends on where you installed
	- Windows: `%LOCALAPPDATA%\trakt-scrobbler`
3. Clone/download this repo to some directory or run `git pull` if you already have it cloned.
4. Run the install script from `scripts` subdirectory for your platform.

## Contributing
Feel free to create a new issue in case you find a bug/want to have a feature added. Proper PRs are welcome.

## Authors
+ [iamkroot](https://www.github.com/iamkroot)

## Acknowledgements
+ Inspired from [TraktForVLC](https://github.com/XaF/TraktForVLC)
+ [mpv-trakt-sync-daemon](https://github.com/stareInTheAir/mpv-trakt-sync-daemon) was a huge help in making the mpv monitor
