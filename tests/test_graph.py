import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from graph import (  # noqa: E402
    RepoFileError,
    build_graph,
    format_graph,
    is_excluded,
    load_test_repo,
    parse_line,
    parse_repo,
)

REPOS = os.path.join(os.path.dirname(__file__), "..", "test_repos")


def source_of(repo):
    """Источник зависимостей по словарю; неизвестные пакеты без зависимостей."""
    return lambda name: list(repo.get(name, []))


class BuildGraphTests(unittest.TestCase):
    """Построение графа обходом в ширину."""

    def test_chain(self):
        """Транзитивные зависимости цепочки попадают в граф."""
        graph = build_graph("A", source_of(
            {"A": ["B"], "B": ["C"], "C": ["D"], "D": []}))
        self.assertEqual(
            graph, {"A": ["B"], "B": ["C"], "C": ["D"], "D": []})

    def test_bfs_order(self):
        """Пакеты обходятся по уровням, общий пакет посещается один раз."""
        repo = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
        self.assertEqual(
            list(build_graph("A", source_of(repo))), ["A", "B", "C", "D"])

    def test_levels_before_depth(self):
        """Обход в ширину: внуки после всех детей."""
        repo = {"A": ["B", "C"], "B": ["D"], "C": ["E"]}
        self.assertEqual(
            list(build_graph("A", source_of(repo))),
            ["A", "B", "C", "D", "E"])

    def test_cycle(self):
        """Цикл не приводит к бесконечному обходу, ребро сохраняется."""
        repo = {"A": ["B"], "B": ["C"], "C": ["A"]}
        graph = build_graph("A", source_of(repo))
        self.assertEqual(graph, repo)

    def test_self_loop(self):
        """Зависимость пакета от самого себя."""
        graph = build_graph("A", source_of({"A": ["A", "B"]}))
        self.assertEqual(graph, {"A": ["A", "B"], "B": []})

    def test_cycle_inside_graph(self):
        """Цикл, не включающий корень."""
        repo = {"A": ["B"], "B": ["C"], "C": ["B"]}
        self.assertEqual(build_graph("A", source_of(repo)), repo)

    def test_undescribed_package_is_leaf(self):
        """Пакет без описания считается листом."""
        graph = build_graph("A", source_of({"A": ["Z"]}))
        self.assertEqual(graph, {"A": ["Z"], "Z": []})

    def test_deep_graph(self):
        """Граф глубиной в сотни уровней строится без ошибок."""
        depth = 300
        repo = {f"P{i}": [f"P{i + 1}"] for i in range(depth)}
        graph = build_graph("P0", source_of(repo))
        self.assertEqual(len(graph), depth + 1)


class FilterTests(unittest.TestCase):
    """Исключение пакетов по подстроке."""

    def test_is_excluded(self):
        """Пустая подстрока ничего не исключает."""
        self.assertFalse(is_excluded("libc6", ""))
        self.assertTrue(is_excluded("libc6", "lib"))
        self.assertFalse(is_excluded("zlib1g", "xyz"))

    def test_filtered_not_in_graph(self):
        """Исключённый пакет не попадает в граф ни узлом, ни ребром."""
        repo = {"A": ["BX", "C"], "BX": ["D"], "C": []}
        graph = build_graph("A", source_of(repo), "X")
        self.assertEqual(graph, {"A": ["C"], "C": []})

    def test_filtered_branch_not_expanded(self):
        """Зависимости исключённого пакета тоже не обходятся."""
        repo = {"A": ["BX"], "BX": ["D"], "D": []}
        self.assertEqual(
            build_graph("A", source_of(repo), "X"), {"A": []})

    def test_package_reachable_other_way_stays(self):
        """Пакет, достижимый и через исключённый, и напрямую, остаётся."""
        repo = {"A": ["BX", "D"], "BX": ["D"], "D": []}
        graph = build_graph("A", source_of(repo), "X")
        self.assertEqual(graph, {"A": ["D"], "D": []})

    def test_root_is_never_excluded(self):
        """Корневой пакет входит в граф, даже если содержит подстроку."""
        graph = build_graph("AX", source_of({"AX": ["B"]}), "X")
        self.assertEqual(graph, {"AX": ["B"], "B": []})


class FormatGraphTests(unittest.TestCase):
    """Текстовый вывод графа."""

    def test_format(self):
        """Заголовок с числом пакетов и строка на каждый пакет."""
        graph = build_graph("A", source_of({"A": ["B", "C"]}))
        self.assertEqual(
            format_graph("A", graph).splitlines(),
            ["Граф зависимостей пакета A (пакетов: 3):",
             "  A -> B, C",
             "  B -> (нет)",
             "  C -> (нет)"],
        )


def repo_path(name):
    """Путь к файлу из папки test_repos."""
    return os.path.join(REPOS, name)


class ParseTests(unittest.TestCase):
    """Разбор строк и файла описания графа."""

    def test_line_with_dependencies(self):
        """Зависимости через пробелы и запятые, повторы убираются."""
        self.assertEqual(parse_line(1, "A: B, C  D B"), ("A", ["B", "C", "D"]))

    def test_line_without_dependencies(self):
        """Пакет без зависимостей."""
        self.assertEqual(parse_line(1, "A:"), ("A", []))

    def test_blank_and_comment(self):
        """Пустые строки и комментарии пропускаются."""
        self.assertIsNone(parse_line(1, "   "))
        self.assertIsNone(parse_line(2, "# комментарий"))

    def test_no_separator(self):
        """Строка без двоеточия."""
        with self.assertRaises(RepoFileError) as context:
            parse_line(3, "A B")
        self.assertIn("строка 3", str(context.exception))

    def test_bad_names(self):
        """Имена не из заглавных латинских букв."""
        for line in ("a: B", "A: b", "A1: B", ": B", "A: B-C"):
            with self.subTest(line=line):
                with self.assertRaises(RepoFileError):
                    parse_line(1, line)

    def test_duplicate_package(self):
        """Повторное описание пакета."""
        with self.assertRaises(RepoFileError) as context:
            parse_repo(["A: B", "A: C"])
        self.assertIn("описан повторно", str(context.exception))

    def test_parse_repo(self):
        """Файл превращается в словарь."""
        self.assertEqual(
            parse_repo(["# c", "A: B", "", "B:"]), {"A": ["B"], "B": []})


class LoadTests(unittest.TestCase):
    """Загрузка файлов тестовых репозиториев."""

    def test_load_diamond(self):
        """Готовый файл читается, неописанный пакет даёт пустой список."""
        source = load_test_repo(repo_path("diamond.txt"), "A")
        self.assertEqual(source("A"), ["B", "C"])
        self.assertEqual(source("D"), [])
        self.assertEqual(source("UNKNOWN"), [])

    def test_source_returns_copy(self):
        """Изменение результата не портит репозиторий."""
        source = load_test_repo(repo_path("diamond.txt"), "A")
        source("A").append("X")
        self.assertEqual(source("A"), ["B", "C"])

    def test_root_not_described(self):
        """Корневой пакет отсутствует в файле."""
        with self.assertRaises(RepoFileError) as context:
            load_test_repo(repo_path("diamond.txt"), "Q")
        self.assertIn("не описан", str(context.exception))

    def test_broken_files(self):
        """Файл с ошибкой формата даёт сообщение с номером строки."""
        with self.assertRaises(RepoFileError) as context:
            load_test_repo(repo_path("broken_syntax.txt"), "A")
        self.assertIn("строка 2", str(context.exception))

    def test_missing_file(self):
        """Несуществующий файл."""
        with self.assertRaises(RepoFileError):
            load_test_repo(repo_path("no_such.txt"), "A")

    def test_bom_and_binary(self):
        """BOM из блокнота Windows допустим, бинарные данные - ошибка."""
        with tempfile.TemporaryDirectory() as folder:
            good = os.path.join(folder, "bom.txt")
            with open(good, "wb") as file:
                file.write(b"\xef\xbb\xbfA: B\n")
            self.assertEqual(load_test_repo(good, "A")("A"), ["B"])
            bad = os.path.join(folder, "bin.txt")
            with open(bad, "wb") as file:
                file.write(b"\xff\xfe\x00A")
            with self.assertRaises(RepoFileError):
                load_test_repo(bad, "A")


if __name__ == "__main__":
    unittest.main()
