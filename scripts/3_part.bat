@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PY=python"
where py >nul 2>nul && set "PY=py"

echo.
echo === 1. Ромб: общий пакет D, обход по уровням ===
%PY% src\main.py --package A --repo test_repos\diamond.txt --test-mode --package-version 1

echo.
echo === 2. Цепочка, корень в середине (с пакета С) ===
%PY% src\main.py --package C --repo test_repos\chain.txt --test-mode --package-version 1

echo.
echo === 3. Цикл из трёх пакетов: A зависит от B, B от C, C от A ===
%PY% src\main.py --package A --repo test_repos\cycle.txt --test-mode --package-version 1

echo.
echo === 4. Большой граф с общим пакетом G и циклом через G ===
%PY% src\main.py --package A --repo test_repos\complex.txt --test-mode --package-version 1

echo.
echo === 5. Тот же граф с исключением пакетов, содержащих G ===
%PY% src\main.py --package A --repo test_repos\complex.txt --test-mode --package-version 1 --filter G

echo.
echo === 6. Ошибка: неверная строка в файле ===
%PY% src\main.py --package A --repo test_repos\broken_syntax.txt --test-mode --package-version 1

echo.
echo === 7. Ошибка: корневой пакет не описан в файле ===
%PY% src\main.py --package Q --repo test_repos\diamond.txt --test-mode --package-version 1

echo.
echo === 8. Ошибка: файл не существует ===
%PY% src\main.py --package A --repo test_repos\no_such.txt --test-mode --package-version 1

echo.
echo === 9. Реальный репозиторий: nginx без пакетов lib ===
%PY% src\main.py --package nginx --repo https://archive.ubuntu.com/ubuntu --package-version 1.24.0-2ubuntu7 --filter lib

pause