@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PY=python"
where py >nul 2>nul && set "PY=py"

echo.
echo === 1. Прямые зависимости nginx ===
%PY% src\main.py --package nginx --repo https://archive.ubuntu.com/ubuntu --package-version 1.24.0-2ubuntu7

echo.
echo === 2. Пакет не найден в репозитории ===
%PY% src\main.py --package no-such-package --repo https://archive.ubuntu.com/ubuntu --package-version 1.0

echo.
echo === 3. Версия не найдена ===
%PY% src\main.py --package nginx --repo https://archive.ubuntu.com/ubuntu --package-version 0.0.1

echo.
echo === 4. Репозиторий недоступен ===
%PY% src\main.py --package nginx --repo https://archive.ubuntu.invalid/ubuntu --package-version 1.24.0-2ubuntu7

echo.
echo === 5. Режим тестирования ===
%PY% src\main.py --package A --repo README.md --test-mode --package-version 1.0

echo.
echo === 6. Другой релиз ===
%PY% src\main.py --package nginx --repo https://archive.ubuntu.com/ubuntu --package-version 1.24.0-2ubuntu7 --release jammy

pause