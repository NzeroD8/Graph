import gzip
import http.client
import urllib.request
import zlib
from typing import Callable, Dict, List, Optional, Tuple

from apt_parser import Entry, collect_entries, parse_dependencies

RELEASE_SUFFIXES = ("", "-updates", "-security")
COMPONENTS = ("main", "universe")
ARCHITECTURE = "amd64"
INDEX_PATH = "dists/{release}/{component}/binary-{arch}/Packages.gz"
TIMEOUT_SECONDS = 30
INDEX_ERRORS = (OSError, EOFError, http.client.HTTPException, zlib.error)

Index = Dict[str, List[Entry]]
DependencySource = Callable[[str], List[str]]


class FetchError(Exception):
    """Ошибка получения данных о пакете из репозитория."""


def build_index_urls(repo: str, release: str) -> List[str]:
    base = repo.rstrip("/")
    return [
        f"{base}/" + INDEX_PATH.format(
            release=release + suffix,
            component=component,
            arch=ARCHITECTURE,
        )
        for suffix in RELEASE_SUFFIXES
        for component in COMPONENTS
    ]


def read_index(url: str) -> Index:
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
        with gzip.open(
            response, "rt", encoding="utf-8", errors="replace"
        ) as lines:
            return collect_entries(lines)


def load_index(repo: str, release: str) -> Tuple[Index, List[str]]:
    urls = build_index_urls(repo, release)
    index: Index = {}
    failures: List[str] = []
    for url in urls:
        try:
            part = read_index(url)
        except INDEX_ERRORS as error:
            failures.append(f"{url}: {error}")
            continue
        for name, entries in part.items():
            index.setdefault(name, []).extend(entries)
    if len(failures) == len(urls):
        raise FetchError(f"репозиторий недоступен: {failures[0]}")
    return index, failures


def pick_version(entries: List[Entry], version: str) -> Optional[Entry]:
    for entry in entries:
        if entry.version == version:
            return entry
    return None


def explain_failure(
    package: str,
    version: str,
    release: str,
    known: List[Entry],
    failed: int,
) -> str:
    if known:
        versions = ", ".join(sorted({entry.version for entry in known}))
        return (
            f"версия {version} пакета «{package}» не найдена "
            f"в релизе {release}; в нём есть: {versions}"
        )
    message = f"пакет «{package}» не найден в релизе {release}"
    if failed:
        message += f" (не удалось прочитать индексов: {failed})"
    return message


def load_dependency_source(
    repo: str, package: str, version: str, release: str
) -> DependencySource:
    index, failures = load_index(repo, release)
    known = index.get(package, [])
    root = pick_version(known, version)
    if root is None:
        raise FetchError(
            explain_failure(package, version, release, known, len(failures))
        )

    def dependencies(name: str) -> List[str]:
        entries = index.get(name)
        if name == package:
            return parse_dependencies(root.dependencies)
        if not entries:
            return []
        return parse_dependencies(entries[-1].dependencies)

    return dependencies
