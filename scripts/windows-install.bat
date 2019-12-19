@echo off

echo Checking poetry install.
where poetry >NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
	echo Poetry not found. Installing.
	pip install poetry || echo Error while installing poetry. Exiting. && goto :EOF
	poetry --version >NUL 2>&1 || echo Still unable to run poetry. Check you PATH variable. && goto :EOF
)

for /f "delims=\" %%a in ("%cd%") do if "%%~nxa"=="scripts" cd ..
 
set install-dir="%LOCALAPPDATA%\trakt-scrobbler"
set cfg-dir="%APPDATA%\trakt-scrobbler\"

echo,
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

echo,
echo Installing to %install-dir%

xcopy /i /s /r /y .\trakt_scrobbler %install-dir%\ >NUL
xcopy /i /r /y pyproject.toml %install-dir%\ >NUL
xcopy /i /r /y poetry.lock %install-dir%\ >NUL

pushd %install-dir%
poetry install --no-dev || echo >&2 "Error while creating venv" && goto :EOF

for /f %%i in ('poetry env info -p') do set py_path=%%i\Scripts\pythonw.exe

echo Setup complete. Starting device authentication.
poetry run python -c "import trakt_interface; trakt_interface.get_access_token()" || echo You can run this script again once the issue is fixed. Quitting. && goto :EOF

echo,
echo Adding to startup commands.

set batch_path="%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\trakt-scrobbler.bat"
echo @echo off >%batch_path%
echo pushd %install-dir% >>%batch_path%
echo start /D %install-dir% "" %py_path% %install-dir%\main.py >>%batch_path%

echo Starting trakt-scrobbler.
start /D %install-dir% "" %py_path% %install-dir%\main.py

echo Done.
:EOF
popd
