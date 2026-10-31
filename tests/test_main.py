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
    main,
)

REPOS = os.path.join(os.path.dirname(__file__), "..", "test_repos")
GOOD_ARGS = [
    "--package", "nginx",
    "--repo", "https://archive.ubuntu.com/ubuntu",
    "--package-version", "1.24.0",
]
OPEN_SOURCE = "main.open_source"
GRAPH = {"nginx": ["libc6", "zlib1g"], "libc6": ["zlib1g"]}


def run_main(args):
    """Запускает main и возвращает код, stdout и stderr."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(args)
    return code, out.getvalue(), err.getvalue()


def test_args(name, package="A", extra=()):
    """Аргументы запуска в режиме тестирования для файла из test_repos."""
    path = os.path.join(REPOS, name)
    return ["--package", package, "--repo", path, "--test-mode",
            "--package-version", "1", *extra]


class MainTests(unittest.TestCase):
    """Обычный режим: источник зависимостей подменён."""

    def test_prints_graph(self):
        """Граф выводится построчно."""
        with mock.patch(OPEN_SOURCE, return_value=lambda n: GRAPH.get(n, [])):
            code, out, err = run_main(GOOD_ARGS)
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(
            out.splitlines(),
            ["Граф зависимостей пакета nginx (пакетов: 3):",
             "  nginx -> libc6, zlib1g",
             "  libc6 -> zlib1g",
             "  zlib1g -> (нет)"],
        )
        self.assertEqual(err, "")

    def test_filter_applied(self):
        """Подстрока из --filter исключает пакеты."""
        with mock.patch(OPEN_SOURCE, return_value=lambda n: GRAPH.get(n, [])):
            _, out, _ = run_main(GOOD_ARGS + ["--filter", "libc"])
        self.assertNotIn("libc6", out)
        self.assertIn("nginx -> zlib1g", out)

    def test_fetch_error(self):
        """Ошибка получения данных идёт в stderr с кодом 3."""
        with mock.patch(OPEN_SOURCE, side_effect=FetchError("нет сети")):
            code, out, err = run_main(GOOD_ARGS)
        self.assertEqual(code, EXIT_FETCH_ERROR)
        self.assertEqual(out, "")
        self.assertEqual(err, "Ошибка: нет сети\n")

    def test_config_error_skips_source(self):
        """Ошибка параметров не приводит к обращению к репозиторию."""
        with mock.patch(OPEN_SOURCE) as open_source:
            code, out, err = run_main(["--package", "Bad"])
        open_source.assert_not_called()
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


class TestModeTests(unittest.TestCase):
    """Режим тестирования на готовых файлах из test_repos."""

    def graph_lines(self, name, package="A", extra=()):
        """Возвращает строки вывода без заголовка."""
        code, out, err = run_main(test_args(name, package, extra))
        self.assertEqual((code, err), (EXIT_OK, ""))
        return out.splitlines()[1:]

    def test_diamond(self):
        """Общий пакет D выводится один раз."""
        self.assertEqual(
            self.graph_lines("diamond.txt"),
            ["  A -> B, C", "  B -> D", "  C -> D", "  D -> (нет)"])

    def test_chain_from_middle(self):
        """Корнем можно сделать любой пакет файла."""
        self.assertEqual(
            self.graph_lines("chain.txt", "C"),
            ["  C -> D", "  D -> (нет)"])

    def test_cycle(self):
        """Цикл A -> B -> C -> A завершается."""
        self.assertEqual(
            self.graph_lines("cycle.txt"),
            ["  A -> B", "  B -> C", "  C -> A"])

    def test_complex_with_filter(self):
        """Фильтр убирает пакет G и всё, что доступно только через него."""
        lines = self.graph_lines("complex.txt", extra=["--filter", "G"])
        self.assertFalse(any("G" in line for line in lines))
        self.assertIn("  E -> H", lines)

    def test_complex_cycle(self):
        """В большом примере цикл G -> B сохранён как ребро."""
        self.assertIn("  G -> B", self.graph_lines("complex.txt"))

    def test_errors(self):
        """Ошибки файла и пакета: stderr и код 3."""
        cases = [
            test_args("broken_syntax.txt"),
            test_args("diamond.txt", package="Q"),
            test_args("no_such.txt"),
        ]
        for args in cases:
            with self.subTest(args=args[3]):
                code, out, err = run_main(args)
                self.assertEqual(out, "")
                self.assertTrue(err.startswith("Ошибка: "))
                self.assertIn(code, (EXIT_FETCH_ERROR, EXIT_CONFIG_ERROR))


if __name__ == "__main__":
    unittest.main()
