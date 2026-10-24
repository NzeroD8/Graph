import contextlib
import io
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import EXIT_CONFIG_ERROR, EXIT_OK, main

GOOD_ARGS = [
    "--package", "nginx",
    "--repo", "https://archive.ubuntu.com/ubuntu",
    "--package-version", "1.24.0",
]


def run_main(args):
    """Запускает main и возвращает код, stdout и stderr."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(args)
    return code, out.getvalue(), err.getvalue()


class MainTests(unittest.TestCase):
    """Поведение точки входа."""

    def test_success_prints_key_value(self):
        """Корректные параметры выводятся построчно."""
        code, out, err = run_main(GOOD_ARGS)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("package: nginx", out)
        self.assertIn("version: 1.24.0", out)
        self.assertEqual(err, "")

    def test_error_goes_to_stderr(self):
        """Ошибка идёт в stderr, stdout пуст."""
        code, out, err = run_main(["--package", "Bad"])
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertEqual(out, "")
        self.assertIn("Ошибка: --package", err)

    def test_each_error_on_own_line(self):
        """Каждая ошибка выводится отдельной строкой."""
        _, _, err = run_main([])
        lines = err.splitlines()
        self.assertTrue(all(line.startswith("Ошибка: ") for line in lines))
        self.assertEqual(len(lines), len(set(lines)))

    def test_help_exits_successfully(self):
        """Справка завершает программу с кодом успеха."""
        with self.assertRaises(SystemExit) as context:
            run_main(["--help"])
        self.assertEqual(context.exception.code, EXIT_OK)


if __name__ == "__main__":
    unittest.main()
