import contextlib
import io
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from extract import FetchError  # noqa: E402
from main import (  # noqa: E402
    EXIT_CONFIG_ERROR,
    EXIT_FETCH_ERROR,
    EXIT_OK,
    TEST_MODE_NOTE,
    main,
)

GOOD_ARGS = [
    "--package", "nginx",
    "--repo", "https://archive.ubuntu.com/ubuntu",
    "--package-version", "1.24.0",
]
FETCH = "main.fetch_dependencies"


def run_main(args):
    """Запускает main и возвращает код, stdout и stderr."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(args)
    return code, out.getvalue(), err.getvalue()


class MainTests(unittest.TestCase):
    """Поведение точки входа."""

    def test_prints_dependencies(self):
        """Прямые зависимости выводятся построчно."""
        with mock.patch(FETCH, return_value=["libc6", "zlib1g"]) as fetch:
            code, out, err = run_main(GOOD_ARGS)
        fetch.assert_called_once_with(
            "https://archive.ubuntu.com/ubuntu", "nginx", "1.24.0", "noble")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(
            out.splitlines(),
            ["Прямые зависимости пакета nginx 1.24.0:",
             "  libc6", "  zlib1g"],
        )
        self.assertEqual(err, "")

    def test_release_is_passed(self):
        """Значение --release передаётся в получение данных."""
        with mock.patch(FETCH, return_value=[]) as fetch:
            run_main(GOOD_ARGS + ["--release", "jammy"])
        self.assertEqual(fetch.call_args.args[3], "jammy")

    def test_no_dependencies(self):
        """Пустой список зависимостей помечается как "нет"."""
        with mock.patch(FETCH, return_value=[]):
            _, out, _ = run_main(GOOD_ARGS)
        self.assertIn("(нет)", out)

    def test_fetch_error(self):
        """Ошибка получения данных идёт в stderr с кодом 3."""
        with mock.patch(FETCH, side_effect=FetchError("нет сети")):
            code, out, err = run_main(GOOD_ARGS)
        self.assertEqual(code, EXIT_FETCH_ERROR)
        self.assertEqual(out, "")
        self.assertEqual(err, "Ошибка: нет сети\n")

    def test_config_error_skips_fetch(self):
        """Ошибка параметров не приводит к обращению к репозиторию."""
        with mock.patch(FETCH) as fetch:
            code, out, err = run_main(["--package", "Bad"])
        fetch.assert_not_called()
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertEqual(out, "")
        self.assertIn("Ошибка: --package", err)

    def test_each_error_on_own_line(self):
        """Каждая ошибка выводится отдельной строкой."""
        _, _, err = run_main([])
        lines = err.splitlines()
        self.assertTrue(all(line.startswith("Ошибка: ") for line in lines))
        self.assertEqual(len(lines), len(set(lines)))

    def test_test_mode_does_not_fetch(self):
        """В режиме тестирования сеть не используется."""
        args = ["--package", "A", "--repo", __file__, "--test-mode",
                "--package-version", "1"]
        with mock.patch(FETCH) as fetch:
            code, out, _ = run_main(args)
        fetch.assert_not_called()
        self.assertEqual(code, EXIT_OK)
        self.assertIn(TEST_MODE_NOTE, out)

    def test_help_exits_successfully(self):
        """Справка завершает программу с кодом успеха."""
        with self.assertRaises(SystemExit) as context:
            run_main(["--help"])
        self.assertEqual(context.exception.code, EXIT_OK)


if __name__ == "__main__":
    unittest.main()
