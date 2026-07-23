@echo off
REM Sesame CLI wrapper for Windows
REM Usage: sesame get, sesame list, sesame add, etc.

setlocal enabledelayedexpansion

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Activate venv and run CLI
call "%SCRIPT_DIR%.venv\Scripts\activate.bat"
python "%SCRIPT_DIR%cli.py" %*

endlocal
