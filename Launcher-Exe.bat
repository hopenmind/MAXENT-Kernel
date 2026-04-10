@echo off
rem
set "EXE=%~dp0Installer\M-E-K.exe"

if exist "%EXE%" (
    start "" "%EXE%"
) else (
    echo Impossible de trouver %EXE%
    pause
)