# Trakt Scrobbler

A trakt.tv scrobbler for your computer.

## What is Trakt?

Automatically scrobble TV show episodes and movies you are watching to [Trakt.tv](https://trakt.tv)! It is a website that keeps a history of everything you've watched!

## What is trakt-scrobbler?

`trakt-scrobbler` is an application that runs in the background and monitors your media players for any new activity. When it detects some file being played, it determines the media info (such as name of the movie/show, episode number, etc.) and sends this to [trakt.tv](https://trakt.tv) servers, so that it can be marked as "Currently Watching" on your profile. No manual intervention required!

## Features

*   Full featured [command line interface](https://github.com/iamkroot/trakt-scrobbler/wiki/trakts-CLI-Reference) to control the service. Just run `trakts`.
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

## Getting Started
Head over to the [wiki](https://github.com/iamkroot/trakt-scrobbler/wiki) for further details.

## Contributing

Feel free to create a new issue in case you find a bug/want to have a feature added. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for more details. Proper PRs are welcome.

## Acknowledgements

*   Inspired from [TraktForVLC](https://github.com/XaF/TraktForVLC)
*   [mpv-trakt-sync-daemon](https://github.com/stareInTheAir/mpv-trakt-sync-daemon) was a huge help in making the mpv monitor
