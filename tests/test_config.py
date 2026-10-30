import os
import unittest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import (
    DEFAULT_OUTPUT,
    DEFAULT_RELEASE,
    NOT_SET,
    ConfigError,
    format_config,
    parse_config,
)

URL = "https://archive.ubuntu.com/ubuntu"
THIS_FILE = os.path.abspath(__file__)
BASE_OPTIONS = {
    "--package": "nginx",
    "--repo": URL,
    "--package-version": "1.24.0-2ubuntu7",
}
REQUIRED_OPTIONS_COUNT = 3
TEST_MODE_FLAG = ["--test-mode"]


def make_args(overrides=None, extra=()):
    """Собирает список аргументов из базовых опций и замен."""
    options = dict(BASE_OPTIONS)
    options.update(overrides or {})
    args = []
    for option, value in options.items():
        args += [option, value]
    return args + list(extra)


def test_mode_args(overrides=None, extra=()):
    """Собирает аргументы для режима тестирования."""
    base = {"--package": "A", "--repo": THIS_FILE}
    base.update(overrides or {})
    return make_args(base, TEST_MODE_FLAG + list(extra))


def errors_for(args):
    """Возвращает сообщения об ошибках или пустой список."""
    try:
        parse_config(args)
    except ConfigError as error:
        return error.messages
    return []


class ParseConfigTests(unittest.TestCase):
    """Корректные наборы параметров."""

    def test_minimal_normal_mode(self):
        """Минимальный набор даёт значения по умолчанию."""
        config = parse_config(make_args())
        self.assertEqual(config.package, "nginx")
        self.assertEqual(config.repo, URL)
        self.assertEqual(config.version, "1.24.0-2ubuntu7")
        self.assertEqual(config.output, DEFAULT_OUTPUT)
        self.assertEqual(config.release, DEFAULT_RELEASE)
        self.assertFalse(config.test_mode)
        self.assertFalse(config.ascii_tree)
        self.assertEqual(config.filter_substring, "")

    def test_all_options(self):
        """Все параметры принимаются."""
        args = make_args(
            {"--output": "deps.svg", "--filter": "lib"},
            ["--ascii-tree"],
        )
        config = parse_config(args)
        self.assertEqual(config.output, "deps.svg")
        self.assertEqual(config.filter_substring, "lib")
        self.assertTrue(config.ascii_tree)

    def test_test_mode_with_existing_file(self):
        """Режим тестирования принимает существующий файл."""
        config = parse_config(test_mode_args())
        self.assertTrue(config.test_mode)
        self.assertEqual(config.package, "A")
        self.assertEqual(config.repo, THIS_FILE)

    def test_valid_versions(self):
        """Версии с эпохой, тильдой и плюсом допустимы."""
        for version in ("1", "2:1.0-1", "1.0~rc1+dfsg-2", "3.2.1ubuntu1"):
            with self.subTest(version=version):
                args = make_args({"--package-version": version})
                self.assertEqual(errors_for(args), [])

    def test_uppercase_svg_extension(self):
        """Расширение .SVG в верхнем регистре допустимо."""
        self.assertEqual(errors_for(make_args({"--output": "G.SVG"})), [])


class PackageErrorTests(unittest.TestCase):
    """Ошибки параметра --package."""

    def test_missing_everything(self):
        """Без аргументов сообщается обо всех обязательных параметрах."""
        errors = errors_for([])
        self.assertEqual(len(errors), REQUIRED_OPTIONS_COUNT)

    def test_empty_package(self):
        """Пустое имя пакета."""
        errors = errors_for(make_args({"--package": ""}))
        self.assertIn("--package", errors[0])

    def test_invalid_names_normal_mode(self):
        """Недопустимые имена в обычном режиме."""
        for name in ("Nginx", "a", "-nginx", "my_pkg", "ng inx", "ПАКЕТ"):
            with self.subTest(name=name):
                errors = errors_for(make_args({"--package": name}))
                self.assertIn("--package", errors[0])

    def test_invalid_names_test_mode(self):
        """В режиме тестирования нужны заглавные латинские буквы."""
        for name in ("a", "nginx", "A1", "A-B"):
            with self.subTest(name=name):
                errors = errors_for(test_mode_args({"--package": name}))
                self.assertIn("--package", errors[0])


class RepoErrorTests(unittest.TestCase):
    """Ошибки параметра --repo."""

    def test_empty_repo(self):
        """Пустой адрес репозитория."""
        errors = errors_for(make_args({"--repo": ""}))
        self.assertIn("--repo", errors[0])

    def test_not_url(self):
        """Строки, не являющиеся http(s)-URL."""
        for repo in ("ftp://host/x", "just text", "http://", "C:\\repo"):
            with self.subTest(repo=repo):
                errors = errors_for(make_args({"--repo": repo}))
                self.assertIn("--repo", errors[0])

    def test_malformed_url(self):
        """Некорректный URL не приводит к падению программы."""
        errors = errors_for(make_args({"--repo": "http://[::1"}))
        self.assertIn("--repo", errors[0])

    def test_missing_test_file(self):
        """Несуществующий файл в режиме тестирования."""
        args = test_mode_args({"--repo": "no_such_file.txt"})
        self.assertIn("не найден", errors_for(args)[0])

    def test_directory_instead_of_file(self):
        """Каталог вместо файла в режиме тестирования."""
        folder = os.path.dirname(THIS_FILE)
        errors = errors_for(test_mode_args({"--repo": folder}))
        self.assertIn("не найден", errors[0])

    def test_url_in_test_mode(self):
        """URL в режиме тестирования."""
        errors = errors_for(test_mode_args({"--repo": URL}))
        self.assertIn("а не URL", errors[0])

    def test_file_in_normal_mode(self):
        """Путь к файлу без --test-mode."""
        errors = errors_for(make_args({"--repo": THIS_FILE}))
        self.assertIn("--test-mode", errors[0])


class OtherErrorTests(unittest.TestCase):
    """Ошибки остальных параметров и разбора аргументов."""

    def test_missing_version(self):
        """Версия не задана."""
        errors = errors_for(make_args({"--package-version": ""}))
        self.assertIn("--package-version", errors[0])

    def test_invalid_versions(self):
        """Недопустимые версии."""
        for version in ("abc", "1.0 beta", "v1.0", "1.0_1", ":1.0"):
            with self.subTest(version=version):
                args = make_args({"--package-version": version})
                self.assertIn("--package-version", errors_for(args)[0])

    def test_invalid_output(self):
        """Недопустимые имена файла изображения."""
        names = ("", "graph.png", "graph", "dir/g.svg", "a\\g.svg", ".svg",
                 "a?b.svg", "a:b.svg")
        for name in names:
            with self.subTest(name=name):
                errors = errors_for(make_args({"--output": name}))
                self.assertIn("--output", errors[0])

    def test_valid_release(self):
        """Кодовые имена релизов допустимы."""
        for release in ("noble", "jammy", "focal"):
            with self.subTest(release=release):
                args = make_args(extra=["--release", release])
                self.assertEqual(errors_for(args), [])

    def test_release_number_becomes_name(self):
        """Номер релиза заменяется кодовым именем."""
        config = parse_config(make_args(extra=["--release", "22.04"]))
        self.assertEqual(config.release, "jammy")

    def test_release_name_kept(self):
        """Кодовое имя остаётся без изменений."""
        config = parse_config(make_args(extra=["--release", "focal"]))
        self.assertEqual(config.release, "focal")

    def test_unknown_release_number(self):
        """Неизвестный номер релиза."""
        errors = errors_for(make_args(extra=["--release", "99.04"]))
        self.assertIn("неизвестный номер релиза", errors[0])

    def test_invalid_release(self):
        """Недопустимые имена релизов."""
        for release in ("", "Noble", "24", "no ble", "noble-updates"):
            with self.subTest(release=release):
                args = make_args(extra=["--release", release])
                self.assertIn("--release", errors_for(args)[0])

    def test_invalid_filter(self):
        """Недопустимые подстроки фильтра."""
        for substring in ("bad filter", "a/b", "строка", "a*"):
            with self.subTest(substring=substring):
                errors = errors_for(make_args({"--filter": substring}))
                self.assertIn("--filter", errors[0])

    def test_valid_filter(self):
        """Допустимые подстроки фильтра."""
        for substring in ("", "lib", "py3-", "a.b+c"):
            with self.subTest(substring=substring):
                args = make_args({"--filter": substring})
                self.assertEqual(errors_for(args), [])

    def test_unknown_option(self):
        """Неизвестная опция."""
        errors = errors_for(make_args(extra=["--depth", "3"]))
        self.assertIn("аргументы командной строки", errors[0])

    def test_option_without_value(self):
        """Опция без значения."""
        errors = errors_for(["--package"])
        self.assertIn("аргументы командной строки", errors[0])

    def test_flag_with_value(self):
        """Флаг, которому передали значение."""
        errors = errors_for(make_args(extra=["--ascii-tree=yes"]))
        self.assertIn("аргументы командной строки", errors[0])

    def test_abbreviation_rejected(self):
        """Сокращённые имена опций не принимаются."""
        errors = errors_for(["--pack", "nginx"])
        self.assertIn("аргументы командной строки", errors[0])

    def test_errors_are_collected(self):
        """Ошибки нескольких параметров выводятся вместе."""
        args = make_args(
            {"--package": "Bad", "--package-version": "x",
             "--output": "g.png"}
        )
        self.assertEqual(len(errors_for(args)), REQUIRED_OPTIONS_COUNT)


class FormatConfigTests(unittest.TestCase):
    """Вывод параметров в формате "ключ: значение"."""

    def test_format_lines(self):
        """Выводятся все восемь ключей в заданном порядке."""
        lines = format_config(parse_config(make_args())).splitlines()
        keys = [line.split(":", 1)[0] for line in lines]
        self.assertEqual(
            keys,
            ["package", "repo", "test_mode", "version", "release", "output",
             "ascii_tree", "filter_substring"],
        )

    def test_format_values(self):
        """Логические значения строчными, пустое - как "не задано"."""
        text = format_config(parse_config(make_args()))
        self.assertIn("test_mode: false", text)
        self.assertIn("ascii_tree: false", text)
        self.assertIn(f"filter_substring: {NOT_SET}", text)
        self.assertIn(f"output: {DEFAULT_OUTPUT}", text)


if __name__ == "__main__":
    unittest.main()
