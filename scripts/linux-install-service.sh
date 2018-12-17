#!/bin/bash
command -v pipenv >/dev/null 2>&1 || { echo >&2 "Please install pipenv first."; exit 1; }

echo "Installing to $HOME/.local/trakt_scrobbler"
cp -r trakt_scrobbler/ $HOME/.local/
cp ./{Pipfile,Pipfile.lock} $HOME/.local/trakt_scrobbler/
cd $HOME/.local/trakt_scrobbler/

pipenv --venv >/dev/null 2>&1 || { pipenv install ; }  # create venv if not present
py_path=$(pipenv --py)

echo "Creating system service."

sudo tee /etc/systemd/system/trakt-scrobbler.service > /dev/null << EOL
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
