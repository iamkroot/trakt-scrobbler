@echo off
where pipenv >NUL 2>&1 || echo Please install pipenv first. && goto :EOF
set install-dir=%APPDATA%\trakt_scrobbler\
echo Installing to %install-dir%
xcopy /s /r /y .\trakt_scrobbler %install-dir% >NUL
xcopy /r /y Pipfile %install-dir% >NUL
xcopy /r /y Pipfile.lock %install-dir% >NUL
pushd %install-dir%
echo Creating virtualenv
pipenv install
for /F "tokens=* USEBACKQ" %%F in (`pipenv --venv`) do (
set venv_path=%%F
)
set py_path=%venv_path%\Scripts\pythonw.exe
echo "Adding to startup commands."
set batch_path="%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\trakt_scrobbler.bat"
echo @echo off >%batch_path%
echo pushd %install-dir% >>%batch_path%
echo start %py_path% %APPDATA%\trakt_scrobbler\main.py >>%batch_path%
popd
:EOF