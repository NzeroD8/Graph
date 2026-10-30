import gzip
import http.client
import urllib.request
import zlib
from typing import List, Optional

from apt_parser import (
    VERSION_FIELD,
    Record,
    direct_dependencies,
    find_records,
)

RELEASE_SUFFIXES = ("", "-updates", "-security")
COMPONENTS = ("main", "universe")
ARCHITECTURE = "amd64"
INDEX_PATH = "dists/{release}/{component}/binary-{arch}/Packages.gz"
TIMEOUT_SECONDS = 30
INDEX_ERRORS = (OSError, EOFError, http.client.HTTPException, zlib.error)


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


def search_index(url: str, package: str) -> List[Record]:
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
        with gzip.open(
            response, "rt", encoding="utf-8", errors="replace"
        ) as lines:
            return find_records(lines, package)


def pick_version(records: List[Record], version: str) -> Optional[Record]:
    for record in records:
        if record.get(VERSION_FIELD) == version:
            return record
    return None


def explain_failure(
    package: str,
    version: str,
    release: str,
    known: List[Record],
    failures: List[str],
    total: int,
) -> str:
    if len(failures) == total:
        return f"репозиторий недоступен: {failures[0]}"
    if known:
        versions = ", ".join(sorted({r[VERSION_FIELD] for r in known}))
        return (
            f"версия {version} пакета «{package}» не найдена "
            f"в релизе {release}; в нём есть: {versions}"
        )
    message = f"пакет «{package}» не найден в релизе {release}"
    if failures:
        message += f" (не удалось прочитать индексов: {len(failures)})"
    return message


def fetch_dependencies(
    repo: str, package: str, version: str, release: str
) -> List[str]:
    urls = build_index_urls(repo, release)
    known: List[Record] = []
    failures: List[str] = []
    for url in urls:
        try:
            records = search_index(url, package)
        except INDEX_ERRORS as error:
            failures.append(f"{url}: {error}")
            continue
        match = pick_version(records, version)
        if match:
            return direct_dependencies(match)
        known += records
    raise FetchError(
        explain_failure(
            package, version, release, known, failures, len(urls)
        )
    )
