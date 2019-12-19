#!/bin/bash

echo "Checking poetry install."
if ! [ -x "$(command -v poetry)" ]; then
  echo "Poetry not found. Installing." >&2
  pip install -q --user poetry || { echo "Error while installing poetry. Exiting." >&2; exit 1; }
  poetry --version >/dev/null 2>&1 || { echo >&2 "Still unable to run poetry. Check you PATH variable."; exit 1; }
fi

[ "${PWD##*/}" == "scripts" ] && cd ..

dest="$HOME/.local/trakt-scrobbler/"
cfg_dir="$HOME/.config/trakt-scrobbler/"
mkdir -p "$dest"
mkdir -p "$cfg_dir"

echo
echo "Checking config file"
if [ ! -e "$cfg_dir/config.toml" ]; then
	if [ ! -e config.toml ]; then
		echo >&2 "config.toml not found in $(pwd) or $cfg_dir".;
		echo "Please go through the Configuration section in README first.";
		exit 1;
	else
		cp config.toml "$cfg_dir"
	fi
else
	echo "config.toml already exists in $cfg_dir".
	echo Please ensure that it matches sample_config.toml, or the app may crash unexpectedly.
fi

echo
echo Installing to "$dest"
cp -r trakt_scrobbler/** "$dest"
cp ./{pyproject.toml,poetry.lock} "$dest"

cd "$dest" || { echo >&2 "Unable to access install location"; exit 1; }

poetry install --no-dev || { echo >&2 "Error while creating venv"; exit 1; }

echo Setup complete. Starting device authentication.
poetry run python -c "import trakt_interface; trakt_interface.get_access_token()" || { echo "You can run this script again once the issue is fixed. Quitting."; exit 1; }

echo
echo Creating system service.

mkdir -p "$HOME"/.config/systemd/user
tee "$HOME"/.config/systemd/user/trakt-scrobbler.service > /dev/null << EOL
[Unit]
Description=Trakt Scrobbler Service

[Service]
ExecStart=$(which poetry) run python main.py
WorkingDirectory=$dest

[Install]
WantedBy=default.target
EOL

systemctl --user daemon-reload
systemctl --user enable trakt-scrobbler

echo Starting trakt-scrobbler.

systemctl --user start trakt-scrobbler

echo Done.
