import sys
from typing import List, Optional, Sequence

from config import Config, ConfigError, format_config, parse_config
from extract import FetchError, fetch_dependencies

EXIT_OK = 0
EXIT_CONFIG_ERROR = 2
EXIT_FETCH_ERROR = 3
INDENT = "  "
TEST_MODE_NOTE = "Режим тестирования пока не поддерживается."


def format_dependencies(config: Config, names: List[str]) -> str:
    title = f"Прямые зависимости пакета {config.package} {config.version}:"
    if not names:
        return f"{title}\n{INDENT}(нет)"
    return "\n".join([title] + [f"{INDENT}{name}" for name in names])


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        config = parse_config(argv)
    except ConfigError as error:
        for message in error.messages:
            print(f"Ошибка: {message}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    """print(format_config(config))"""
    if config.test_mode:
        print(TEST_MODE_NOTE)
        return EXIT_OK
    try:
        names = fetch_dependencies(
            config.repo, config.package, config.version, config.release
        )
    except FetchError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return EXIT_FETCH_ERROR
    print(format_dependencies(config, names))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
