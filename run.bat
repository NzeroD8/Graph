@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PY=python"
where py >nul 2>nul && set "PY=py"
%PY% src\main.py %*
pause
