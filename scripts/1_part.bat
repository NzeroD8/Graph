@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PY=python"
where py >nul 2>nul && set "PY=py"

echo.
echo === 1. Корректный запуск (обычный режим) ===
%PY% src\main.py --package nginx --repo https://archive.ubuntu.com/ubuntu --package-version 1.24.0-2ubuntu7 --output deps.svg --ascii-tree --filter lib

echo.
echo === 2. Корректный запуск (режим тестирования) ===
%PY% src\main.py --package A --repo README.md --test-mode --package-version 1.0

echo.
echo === 3. Нет обязательных параметров ===
%PY% src\main.py

echo.
echo === 4. Неверное имя пакета ===
%PY% src\main.py --package Nginx --repo https://archive.ubuntu.com/ubuntu --package-version 1.0

echo.
echo === 5. Репозиторий не похож на URL ===
%PY% src\main.py --package nginx --repo ftp://host/ubuntu --package-version 1.0

echo.
echo === 6. Файл тестового репозитория не найден ===
%PY% src\main.py --package A --repo no_such_file.txt --test-mode --package-version 1.0

echo.
echo === 7. Неверная версия ===
%PY% src\main.py --package nginx --repo https://archive.ubuntu.com/ubuntu --package-version abc

echo.
echo === 8. Неверное имя файла изображения ===
%PY% src\main.py --package nginx --repo https://archive.ubuntu.com/ubuntu --package-version 1.0 --output graph.png

echo.
echo === 9. Неверная подстрока фильтра ===
%PY% src\main.py --package nginx --repo https://archive.ubuntu.com/ubuntu --package-version 1.0 --filter "bad filter"

echo.
echo === 10. Неизвестная опция и флаг со значением ===
%PY% src\main.py --depth 3
%PY% src\main.py --ascii-tree=yes

echo.
echo === 11. Неверный релиз ===
%PY% src\main.py --package nginx --repo https://archive.ubuntu.com/ubuntu --package-version 1.0 --release Noble

pause