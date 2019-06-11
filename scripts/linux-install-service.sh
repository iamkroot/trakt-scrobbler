#!/bin/bash
command -v pipenv >/dev/null 2>&1 || { echo >&2 "Please install pipenv first."; exit 1; }
[ "${PWD##*/}" == "scripts" ] && cd ..
dest=$HOME/.local/trakt-scrobbler
echo Installing to $dest
cp -r trakt_scrobbler/ $dest
cp ./{Pipfile,Pipfile.lock} $dest
cd $dest

pipenv --venv >/dev/null 2>&1 || { pipenv install ; }  # create venv if not present
py_path=$(pipenv --py)

echo Creating system service.

mkdir -p $HOME/.config/systemd/user 
tee $HOME/.config/systemd/user/trakt-scrobbler.service > /dev/null << EOL
[Unit]
Description=Trakt Scrobbler Service

[Service]
ExecStart=$py_path main.py
WorkingDirectory=$dest

[Install]
WantedBy=default.target
EOL

systemctl --user daemon-reload
systemctl --user enable trakt-scrobbler

echo Setup complete.
