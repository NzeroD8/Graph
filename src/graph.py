import re
from typing import Dict, Iterable, List, Optional, Tuple

from config import TEST_PACKAGE_PATTERN
from extract import DependencySource, FetchError

INDENT = "  "
ARROW = " -> "
NO_DEPENDENCIES = "(нет)"
SEPARATOR = ":"
COMMENT_PREFIX = "#"
LIST_SEPARATORS = re.compile(r"[\s,]+")
FILE_ENCODING = "utf-8-sig"

Graph = Dict[str, List[str]]
Repo = Dict[str, List[str]]


class RepoFileError(FetchError):
    """Ошибка чтения файла тестового репозитория."""


def check_name(number: int, name: str) -> None:
    if not TEST_PACKAGE_PATTERN.fullmatch(name):
        raise RepoFileError(
            f"строка {number}: имя «{name}» недопустимо: "
            "нужны заглавные латинские буквы"
        )


def parse_line(number: int, line: str) -> Optional[Tuple[str, List[str]]]:
    text = line.strip()
    if not text or text.startswith(COMMENT_PREFIX):
        return None
    name, separator, rest = text.partition(SEPARATOR)
    if not separator:
        raise RepoFileError(
            f"строка {number}: ожидается вид «ИМЯ: зависимости»"
        )
    name = name.strip()
    check_name(number, name)
    names: List[str] = []
    for dependency in LIST_SEPARATORS.split(rest.strip()):
        if not dependency:
            continue
        check_name(number, dependency)
        if dependency not in names:
            names.append(dependency)
    return name, names


def parse_repo(lines: Iterable[str]) -> Repo:
    repo: Repo = {}
    for number, line in enumerate(lines, start=1):
        parsed = parse_line(number, line)
        if parsed is None:
            continue
        name, dependencies = parsed
        if name in repo:
            raise RepoFileError(
                f"строка {number}: пакет «{name}» описан повторно"
            )
        repo[name] = dependencies
    return repo


def load_test_repo(path: str, package: str) -> DependencySource:
    try:
        with open(path, encoding=FILE_ENCODING) as file:
            repo = parse_repo(file)
    except (OSError, UnicodeDecodeError) as error:
        raise RepoFileError(f"не удалось прочитать {path}: {error}")
    if package not in repo:
        raise RepoFileError(f"пакет «{package}» не описан в файле {path}")

    def dependencies(name: str) -> List[str]:
        return list(repo.get(name, []))

    return dependencies


def is_excluded(name: str, substring: str) -> bool:
    return bool(substring) and substring in name


def visit_level(
    level: List[str],
    graph: Graph,
    source: DependencySource,
    substring: str,
) -> None:
    next_level: List[str] = []
    for name in level:
        dependencies = [
            item
            for item in source(name)
            if not is_excluded(item, substring)
        ]
        graph[name] = dependencies
        for item in dependencies:
            if item not in graph and item not in next_level:
                next_level.append(item)
    if next_level:
        visit_level(next_level, graph, source, substring)


def build_graph(
    root: str, source: DependencySource, substring: str = ""
) -> Graph:
    graph: Graph = {}
    visit_level([root], graph, source, substring)
    return graph


def format_graph(root: str, graph: Graph) -> str:
    lines = [f"Граф зависимостей пакета {root} (пакетов: {len(graph)}):"]
    for name, dependencies in graph.items():
        targets = ", ".join(dependencies) or NO_DEPENDENCIES
        lines.append(f"{INDENT}{name}{ARROW}{targets}")
    return "\n".join(lines)
