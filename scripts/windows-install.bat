@echo off
where pipenv >NUL 2>&1 || echo Please install pipenv first. && goto :EOF

for /f "delims=\" %%a in ("%cd%") do if "%%~nxa"=="scripts" cd ..

set install-dir="%LOCALAPPDATA%\trakt-scrobbler"
set cfg-dir="%APPDATA%\trakt-scrobbler\"

echo Checking config file
if not exist %cfg-dir%config.toml (
	if not exist config.toml (
		echo config.toml not found in %cd% or %cfg-dir%.
		echo Please go through the Configuration section in README first.
		goto :EOF
	) else (
		xcopy /i /r /y config.toml %cfg-dir% >NUL
	)
) else (
	echo config.toml already exists in %cfg-dir%.
	echo Please ensure that it matches sample_config.toml, or the app may crash unexpectedly.
)

echo
echo Installing to %install-dir%

xcopy /i /s /r /y .\trakt_scrobbler %install-dir%\ >NUL
xcopy /i /r /y Pipfile.lock %install-dir%\ >NUL

pushd %install-dir%
pipenv --venv >NUL 2>&1 && pipenv clean
pipenv sync || echo >&2 "Error while creating venv" && goto :EOF

for /F "tokens=* USEBACKQ" %%F in (`pipenv --venv`) do set venv_path=%%F
set py_path="%venv_path%\Scripts\pythonw.exe"

echo Setup complete. Starting device authentication.
pipenv run python -c "import trakt_interface; trakt_interface.get_access_token()" || echo "You can run this script again once the issue is fixed. Quitting." && goto :EOF

echo
echo Adding to startup commands.

set batch_path="%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\trakt-scrobbler.bat"
echo @echo off >%batch_path%
echo pushd %install-dir% >>%batch_path%
echo start %py_path% %install-dir%\main.py >>%batch_path%

popd

%py_path% %install-dir%\main.py

echo Done.
:EOF
