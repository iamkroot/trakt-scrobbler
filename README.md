# Trakt Scrobbler
Simple python project to automatically scrobble media information to [Trakt.tv](https://trakt.tv). Fully pluggable, which enables taking data from multiple players at the *same* time.

## Features
+ Uses [guessit](https://github.com/guessit-io/guessit) to extract media information from its file path. For cases when it misidentifies the files, you can specify a regex to manually extract the necessary details.
+ Scrobbling is independent of the player(s) where the media is played. Support for new players can thus be easily added.
+ Currently has support for:
	+ [VLC](https://www.videolan.org/vlc/) (via web interface)
	+ [MPV](https://mpv.io) (via IPC server)
	+ [MPC-BE](https://sourceforge.net/projects/mpcbe/) (via web interface).
	+ [MPC-HC](https://mpc-hc.org) (via web interface).

## Getting started
### Installation
1. Clone the repo to a directory of your choice.
2. Ensure you have Python 3.6 or higher installed, and in your system `PATH`.
3. Run `pip install pipenv` to install pipenv in your system.

#### Linux
At the root of cloned project directory, run `sudo env "PATH=$PATH" scripts/linux-install-service.sh`. This will install the files in your $HOME/.local/ directory, create the virtualenv, and also enable the startup service.

#### Windows
At the root of cloned project directory, run `scripts\windows-install.bat`. This will install the files in your %APPDATA% directory, create the virtualenv, and also enable the startup service.

#### MacOS
I will try to make a install script for Mac soon. Till then, here are the manual steps you can follow:
1. Inside the project directory root, run `pipenv install`. This will create a virtualenv, and install the necessary requirements.
2. Run `pipenv --py` to find the location of python interpreter of virtualenv. 
3. Edit the `scripts/trakt_scrobbler.plist` file to add the correct folder path of the project.
4. `cp scripts/trakt_scrobbler.plist ~/Library/LaunchAgents/`
5. `launchctl load ~/Library/LaunchAgents/trakt_scrobbler.plist`

### Setting up
#### Players
+ VLC: Enable the Lua Web Interface from advanced options. Don't forget to specify the password in Lua options.

	![VLC Web Interface](https://wiki.videolan.org/images/thumb/VLC_2.0_Activate_HTTP.png/450px-VLC_2.0_Activate_HTTP.png)

+ MPV: Enable the [JSON IPC](https://mpv.io/manual/master/#json-ipc), either via the mpv.conf file, or by passing it as a command line option.

+ MPC-BE/MPC-HC: Enable the web interface from Options.

#### Configuration
All you have to do now is create a `config.toml` file with the required parameters. See `sample_config.toml`.

Parameter | Explanation |
--------- | -----------
`fileinfo.whitelist`| List of strings \| Default: `[]` <br> List of directories you want to be scanned for shows or movies. If empty, all files played in the player are scanned. You can prevent the program from scanning all played files if your shows and movies are located in fixed directories. If possible you should use this option to minimize traffic on the Trakt API.
`fileinfo.include_regexes`| Dict of list of strings \| Default: `{}` <br> If you find that the default module for identifying media info ([guessit](https://github.com/guessit-io/guessit)) is misidentifying some titles, you can specify the regex for that file path. <br> The regex should have posix-like path, and not Windows' `\` to separate directories. <br>The minimum required information is the title of the file, and episode number in the case of TV Shows. If season is not found, it defaults to 1.
`players.priorites`| List of strings <br> Specify the decreasing order of priority for players which are to be monitored for scrobbling. In case multiple players are playing a media, the media from player with higher priority will be scrobbled as playing, and others will be scrobbled stop.
Other player specific parameters| See sample config for the required attributes.

### Running
After setting up `config.toml`, type `python main.py` to start the program.
During the first run, you will be prompted to authorize the program to access the Trakt.tv API. Follow the steps on screen to finish the process.

That's it! Now the program will automatically monitor the enabled players for media information, and scrobble the relevant details to Trakt.

## Contributing
Feel free to create a new issue in case you find a bug/want to have a feature added. Proper PRs are welcome.

## Authors
+ [Krut Patel](https://www.github.com/mach64)

## Acknowledgements
+ Inspired from [TraktForVLC](https://github.com/XaF/TraktForVLC)
+ [mpv-trakt-sync-daemon](https://github.com/stareInTheAir/mpv-trakt-sync-daemon) was a huge help in making the mpv monitor