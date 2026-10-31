import sys
from typing import Optional, Sequence

from config import Config, ConfigError, parse_config
from extract import DependencySource, FetchError, load_dependency_source
from graph import build_graph, format_graph, load_test_repo

EXIT_OK = 0
EXIT_CONFIG_ERROR = 2
EXIT_FETCH_ERROR = 3


def open_source(config: Config) -> DependencySource:
    if config.test_mode:
        return load_test_repo(config.repo, config.package)
    return load_dependency_source(
        config.repo, config.package, config.version, config.release
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        config = parse_config(argv)
    except ConfigError as error:
        for message in error.messages:
            print(f"Ошибка: {message}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    try:
        source = open_source(config)
    except FetchError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return EXIT_FETCH_ERROR
    graph = build_graph(config.package, source, config.filter_substring)
    print(format_graph(config.package, graph))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

