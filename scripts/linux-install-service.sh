#!/bin/bash

if [ $UID != 0 ] ; then
    echo "Please use 'sudo' or log in as root."
    exit 255
fi
command -v pipenv >/dev/null 2>&1 || { echo >&2 "Please install pipenv first."; exit 1; }

echo "Installing to $HOME/.local/trakt_scrobbler"
sudo cp -r trakt_scrobbler/ $HOME/.local/
sudo cp ./{Pipfile,Pipfile.lock} $HOME/.local/trakt_scrobbler/
cd $HOME/.local/trakt_scrobbler/

pipenv --venv >/dev/null 2>&1 || { pipenv install ; }  # create venv if not present
py_path=$(pipenv --py)

echo "Creating system service."
sudo cat > /etc/systemd/system/trakt-scrobbler.service <<EOL
[Unit]
Description=Trakt Scrobbler
After=network.target

[Service]
ExecStart=$py_path main.py
WorkingDirectory=$HOME/.local/trakt_scrobbler
Restart=on-failure
KillSignal=SIGINT

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload
sudo systemctl enable trakt-scrobbler.service
