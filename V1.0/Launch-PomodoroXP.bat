@echo off
setlocal

rem Repository location. Update this if you move the project.
set "APP_DIR=C:\Users\Luke\GitHub_Dev\pomodoroXP"

if not exist "%APP_DIR%\app.py" (
    echo Could not find PomodoroXP at:
    echo %APP_DIR%
    pause
    exit /b 1
)

if exist "%APP_DIR%\.venv\Scripts\pythonw.exe" (
    set "PYTHON=%APP_DIR%\.venv\Scripts\pythonw.exe"
) else (
    set "PYTHON=pythonw"
)

pushd "%APP_DIR%"
start "" /D "%APP_DIR%" "%PYTHON%" app.py
set "EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %EXIT_CODE%
