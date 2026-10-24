import argparse
import os
import re
from dataclasses import asdict, dataclass
from typing import List, NoReturn, Optional, Sequence
from urllib.parse import urlparse

DEFAULT_OUTPUT = "graph.svg"
SVG_EXTENSION = ".svg"
URL_SCHEMES = ("http", "https")
NOT_SET = "(не задано)"

PACKAGE_PATTERN = re.compile(r"[a-z0-9][a-z0-9+.\-]+")
TEST_PACKAGE_PATTERN = re.compile(r"[A-Z]+")
VERSION_PATTERN = re.compile(r"(\d+:)?\d[A-Za-z0-9.+~\-]*")
FILTER_PATTERN = re.compile(r"[A-Za-z0-9+.\-]*")
BAD_FILE_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass
class Config:
    package: str
    repo: str
    test_mode: bool
    version: str
    output: str
    ascii_tree: bool
    filter_substring: str


class ConfigError(Exception):
    def __init__(self, messages: List[str]) -> None:
        super().__init__("; ".join(messages))
        self.messages = messages


class ConfigParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ConfigError(
            [f"неверные аргументы командной строки ({message})"]
        )


def add_source_options(parser: ConfigParser) -> None:
    parser.add_argument(
        "--package", default="", help="имя анализируемого пакета"
    )
    parser.add_argument(
        "--repo",
        default="",
        help="URL репозитория или путь к файлу тестового репозитория",
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="работать с файлом тестового репозитория вместо URL",
    )
    parser.add_argument(
        "--package-version",
        dest="version",
        default="",
        help="версия анализируемого пакета",
    )


def add_output_options(parser: ConfigParser) -> None:
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="имя файла с изображением графа",
    )
    parser.add_argument(
        "--ascii-tree",
        action="store_true",
        help="выводить зависимости в виде ASCII-дерева",
    )
    parser.add_argument(
        "--filter",
        dest="filter_substring",
        default="",
        help="не учитывать пакеты, в имени которых есть эта подстрока",
    )


def build_parser() -> ConfigParser:
    parser = ConfigParser(
        prog="main.py",
        description="Инструмент визуализации графа зависимостей пакетов.",
        allow_abbrev=False,
    )
    add_source_options(parser)
    add_output_options(parser)
    return parser


def is_http_url(text: str) -> bool:
    try:
        parsed = urlparse(text)
    except ValueError:
        return False
    return parsed.scheme in URL_SCHEMES and bool(parsed.netloc)


def check_package(package: str, test_mode: bool) -> Optional[str]:
    if not package:
        return "имя пакета не задано"
    if test_mode:
        if TEST_PACKAGE_PATTERN.fullmatch(package):
            return None
        return (
            f"имя «{package}» недопустимо: в режиме тестирования пакеты "
            "называются заглавными латинскими буквами"
        )
    if PACKAGE_PATTERN.fullmatch(package):
        return None
    return (
        f"имя «{package}» недопустимо: нужны строчные латинские буквы, "
        "цифры и символы + - . (не короче двух символов, первый символ — "
        "буква или цифра)"
    )


def check_test_repo(path: str) -> Optional[str]:
    if is_http_url(path):
        return "в режиме тестирования нужен путь к файлу, а не URL"
    if not os.path.isfile(path):
        return f"файл не найден: {path}"
    if not os.access(path, os.R_OK):
        return f"файл недоступен для чтения: {path}"
    return None


def check_repo(repo: str, test_mode: bool) -> Optional[str]:
    if not repo:
        return "URL или путь к файлу репозитория не задан"
    if test_mode:
        return check_test_repo(repo)
    if is_http_url(repo):
        return None
    return (
        f"«{repo}» не похоже на URL: ожидается вид http(s)://хост/путь"
        "(для файла тестового репозитория добавьте --test-mode)"
    )


def check_version(version: str) -> Optional[str]:
    if not version:
        return "версия пакета не задана"
    if VERSION_PATTERN.fullmatch(version):
        return None
    return (
        f"версия «{version}» версия должна начинаться "
        "с цифры и содержать только буквы, цифры и символы . + ~ -, "
        "например 1.24.0-2ubuntu7"
    )


def check_output(name: str) -> Optional[str]:
    if not name:
        return "имя файла не задано"
    if BAD_FILE_CHARS_PATTERN.search(name):
        return (
            f"имя «{name}» содержит недопустимые символы или путь "
            '(нельзя < > : " / \\ | ? *), нужно только имя файла'
        )
    if len(name) <= len(SVG_EXTENSION) or not (
        name.lower().endswith(SVG_EXTENSION)
    ):
        return (
            f"имя «{name}» недопустимо: нужно имя файла "
            f"с расширением {SVG_EXTENSION}"
        )
    return None


def check_filter(substring: str) -> Optional[str]:
    if FILTER_PATTERN.fullmatch(substring):
        return None
    return (
        f"подстрока «{substring}» недопустима: можно использовать "
        "латинские буквы, цифры и символы + - ."
    )


def collect_errors(config: Config) -> List[str]:
    checks = (
        ("--package", check_package(config.package, config.test_mode)),
        ("--repo", check_repo(config.repo, config.test_mode)),
        ("--package-version", check_version(config.version)),
        ("--output", check_output(config.output)),
        ("--filter", check_filter(config.filter_substring)),
    )
    return [f"{option}: {message}" for option, message in checks if message]


def parse_config(argv: Optional[Sequence[str]] = None) -> Config:
    args = build_parser().parse_args(argv)
    config = Config(**vars(args))
    errors = collect_errors(config)
    if errors:
        raise ConfigError(errors)
    return config


def format_value(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value) if value else NOT_SET


def format_config(config: Config) -> str:
    return "\n".join(
        f"{key}: {format_value(value)}"
        for key, value in asdict(config).items()
    )
