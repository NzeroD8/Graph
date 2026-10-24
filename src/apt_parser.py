import re
from typing import Dict, Iterable, Iterator, List

PACKAGE_FIELD = "Package"
VERSION_FIELD = "Version"
DEPENDENCY_FIELDS = ("Pre-Depends", "Depends")
CONTINUATION_PREFIXES = (" ", "\t")
ALTERNATIVE_SEPARATORS = re.compile(r"[,|]")
NAME_PATTERN = re.compile(r"\s*([a-z0-9][a-z0-9+.\-]*)")

Record = Dict[str, str]


def parse_record(lines: Iterable[str]) -> Record:
    fields: Record = {}
    key = ""
    for line in lines:
        if line.startswith(CONTINUATION_PREFIXES):
            if key:
                fields[key] += "\n" + line.strip()
            continue
        name, separator, value = line.partition(":")
        if separator:
            key = name
            fields[key] = value.strip()
    return fields


def iter_records(lines: Iterable[str]) -> Iterator[Record]:
    block: List[str] = []
    for line in lines:
        if line.strip():
            block.append(line.rstrip("\n"))
        elif block:
            yield parse_record(block)
            block = []
    if block:
        yield parse_record(block)


def find_records(lines: Iterable[str], package: str) -> List[Record]:
    return [
        record
        for record in iter_records(lines)
        if record.get(PACKAGE_FIELD) == package
    ]


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


def direct_dependencies(record: Record) -> List[str]:
    parts = [record[field] for field in DEPENDENCY_FIELDS if field in record]
    return parse_dependencies(", ".join(parts))
