import re
from typing import (
    Collection,
    Dict,
    Iterable,
    Iterator,
    List,
    NamedTuple,
    Optional,
)

PACKAGE_FIELD = "Package"
VERSION_FIELD = "Version"
DEPENDENCY_FIELDS = ("Pre-Depends", "Depends")
INDEX_FIELDS = frozenset((PACKAGE_FIELD, VERSION_FIELD) + DEPENDENCY_FIELDS)
CONTINUATION_PREFIXES = (" ", "\t")
ALTERNATIVE_SEPARATORS = re.compile(r"[,|]")
NAME_PATTERN = re.compile(r"\s*([a-z0-9][a-z0-9+.\-]*)")

Record = Dict[str, str]


class Entry(NamedTuple):
    version: str
    dependencies: str


def parse_record(
    lines: Iterable[str], fields: Optional[Collection[str]] = None
) -> Record:
    record: Record = {}
    key = ""
    for line in lines:
        if line.startswith(CONTINUATION_PREFIXES):
            if key:
                record[key] += "\n" + line.strip()
            continue
        name, separator, value = line.partition(":")
        wanted = fields is None or name in fields
        key = name if separator and wanted else ""
        if key:
            record[key] = value.strip()
    return record


def iter_records(
    lines: Iterable[str], fields: Optional[Collection[str]] = None
) -> Iterator[Record]:
    block: List[str] = []
    for line in lines:
        if line.strip():
            block.append(line.rstrip("\n"))
        elif block:
            yield parse_record(block, fields)
            block = []
    if block:
        yield parse_record(block, fields)


def dependencies_text(record: Record) -> str:
    parts = [record[field] for field in DEPENDENCY_FIELDS if field in record]
    return ", ".join(parts)


def collect_entries(lines: Iterable[str]) -> Dict[str, List[Entry]]:
    entries: Dict[str, List[Entry]] = {}
    for record in iter_records(lines, INDEX_FIELDS):
        name = record.get(PACKAGE_FIELD)
        if name and VERSION_FIELD in record:
            entry = Entry(record[VERSION_FIELD], dependencies_text(record))
            entries.setdefault(name, []).append(entry)
    return entries


def extract_name(alternative: str) -> str:
    match = NAME_PATTERN.match(alternative)
    return match.group(1) if match else ""


def parse_dependencies(value: str) -> List[str]:
    names: List[str] = []
    for alternative in ALTERNATIVE_SEPARATORS.split(value):
        name = extract_name(alternative)
        if name and name not in names:
            names.append(name)
    return names
