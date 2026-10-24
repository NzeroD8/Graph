import sys
from typing import Optional, Sequence

from config import ConfigError, format_config, parse_config

EXIT_OK = 0
EXIT_CONFIG_ERROR = 2


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        config = parse_config(argv)
    except ConfigError as error:
        for message in error.messages:
            print(f"Ошибка: {message}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    print(format_config(config))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
