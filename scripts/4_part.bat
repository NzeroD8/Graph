@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PY=python"
where py >nul 2>nul && set "PY=py"

echo.
echo === 1. Ромб: общий пакет D, обход по уровням ===
%PY% src\main.py --package A --repo test_repos\diamond.txt --test-mode --package-version 1 --load-order

echo.
echo === 2. Цепочка: сначала самая глубокая зависимость ===
%PY% src\main.py --package A --repo test_repos\chain.txt --test-mode --package-version 1 --load-order

echo.
echo === 3. Цикл из трёх пакетов: A зависит от B, B от C, C от A ===
%PY% src\main.py --package A --repo test_repos\cycle.txt --test-mode --package-version 1 --load-order

echo.
echo === 4. Большой граф с общим пакетом G и циклом через G ===
%PY% src\main.py --package A --repo test_repos\complex.txt --test-mode --package-version 1 --load-order

echo.
echo === 5. Тот же граф с исключением пакетов, содержащих G ===
%PY% src\main.py --package A --repo test_repos\complex.txt --test-mode --package-version 1 --load-order --filter G

echo.
echo === 6. Реальный репозиторий: порядок загрузки nginx ===
%PY% src\main.py --package nginx --repo https://archive.ubuntu.com/ubuntu --package-version 1.24.0-2ubuntu7 --load-order

pause
