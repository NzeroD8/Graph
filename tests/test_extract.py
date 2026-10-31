import gzip
import http.server
import os
import sys
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from apt_parser import Entry  # noqa: E402
from extract import (  # noqa: E402
    ARCHITECTURE,
    COMPONENTS,
    RELEASE_SUFFIXES,
    FetchError,
    build_index_urls,
    explain_failure,
    load_dependency_source,
    load_index,
    pick_version,
)

RECORD = "Package: {}\nVersion: {}\nDepends: {}\n\n"
INDEX_FORMAT = "/ubuntu/dists/{}/{}/binary-" + ARCHITECTURE + "/Packages.gz"
NOT_FOUND = 404
NOBLE = "noble"
OLD = "1.24.0-2ubuntu7"
NEW = "1.24.0-2ubuntu7.5"


def route(release, component):
    """Путь файла Packages.gz для пары «релиз, компонент»."""
    return INDEX_FORMAT.format(release, component)


def packed(*records):
    """Сжимает записи (имя, версия, зависимости) в формат Packages.gz."""
    text = "".join(RECORD.format(*record) for record in records)
    return gzip.compress(text.encode())


def make_handler(routes):
    """Создаёт обработчик HTTP, отдающий байты по словарю путей."""

    class Handler(http.server.BaseHTTPRequestHandler):
        """Обработчик GET-запросов тестового репозитория."""

        def do_GET(self):
            """Отдаёт файл из словаря или ответ 404."""
            body = routes.get(self.path)
            self.send_response(NOT_FOUND if body is None else 200)
            self.end_headers()
            if body is not None:
                self.wfile.write(body)

        def log_message(self, *args):
            """Отключает вывод журнала запросов."""

    return Handler


class ExtractTests(unittest.TestCase):
    """Загрузка индексов и источник зависимостей через локальный сервер."""

    @classmethod
    def setUpClass(cls):
        """Запускает сервер с индексами двух релизов."""
        routes = {
            route("noble", "main"): packed(
                ("nginx", OLD, "libc6 (>= 2.34), zlib1g"),
                ("libc6", "2.39", "libgcc-s1"),
                ("libgcc-s1", "14", "libc6"),
            ),
            route("noble-updates", "main"): packed(
                ("nginx", NEW, "libc6, openssl"),
                ("libc6", "2.39.1", "libgcc-s1, newdep"),
            ),
            route("noble", "universe"): b"not a gzip file",
            route("jammy", "main"): packed(
                ("nginx", "1.18.0-6ubuntu14", "libc6, zlib1g"),
            ),
        }
        cls.server = http.server.HTTPServer(
            ("127.0.0.1", 0), make_handler(routes))
        port = cls.server.server_address[1]
        cls.repo = f"http://127.0.0.1:{port}/ubuntu"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        """Останавливает сервер."""
        cls.server.shutdown()
        cls.server.server_close()

    def test_build_index_urls(self):
        """Адресов столько, сколько пар «суффикс релиза, компонент»."""
        urls = build_index_urls("https://h/ubuntu/", NOBLE)
        self.assertEqual(len(urls), len(RELEASE_SUFFIXES) * len(COMPONENTS))
        self.assertEqual(urls[0], "https://h/ubuntu/" + route(
            "noble", "main")[len("/ubuntu/"):])
        self.assertIn("dists/noble-security/universe/", urls[-1])

    def test_load_index_merges_and_counts_failures(self):
        """Индексы объединяются, битый и отсутствующие учитываются."""
        index, failures = load_index(self.repo, NOBLE)
        self.assertEqual([e.version for e in index["nginx"]], [OLD, NEW])
        self.assertEqual(len(failures), 4)

    def test_root_version_and_transitive_dependencies(self):
        """Корень берётся нужной версии, остальные - последней записью."""
        source = load_dependency_source(self.repo, "nginx", OLD, NOBLE)
        self.assertEqual(source("nginx"), ["libc6", "zlib1g"])
        self.assertEqual(source("libc6"), ["libgcc-s1", "newdep"])
        self.assertEqual(source("libgcc-s1"), ["libc6"])

    def test_root_from_updates(self):
        """Версия из -updates выбирается точно."""
        source = load_dependency_source(self.repo, "nginx", NEW, NOBLE)
        self.assertEqual(source("nginx"), ["libc6", "openssl"])

    def test_unknown_package_has_no_dependencies(self):
        """Виртуальный или неописанный пакет считается листом."""
        source = load_dependency_source(self.repo, "nginx", OLD, NOBLE)
        self.assertEqual(source("zlib1g"), [])

    def test_other_release(self):
        """Релиз берётся из параметра."""
        source = load_dependency_source(
            self.repo, "nginx", "1.18.0-6ubuntu14", "jammy")
        self.assertEqual(source("nginx"), ["libc6", "zlib1g"])

    def test_version_of_other_release(self):
        """Версия noble не находится в jammy, релиз назван в ошибке."""
        with self.assertRaises(FetchError) as context:
            load_dependency_source(self.repo, "nginx", OLD, "jammy")
        text = str(context.exception)
        self.assertIn("в релизе jammy", text)
        self.assertIn("1.18.0-6ubuntu14", text)
        self.assertNotIn(NEW, text)

    def test_version_not_found(self):
        """Неизвестная версия: в ошибке перечислены доступные."""
        with self.assertRaises(FetchError) as context:
            load_dependency_source(self.repo, "nginx", "9.9", NOBLE)
        text = str(context.exception)
        self.assertIn("версия 9.9", text)
        self.assertIn(NEW, text)

    def test_package_not_found(self):
        """Неизвестный пакет."""
        with self.assertRaises(FetchError) as context:
            load_dependency_source(self.repo, "nothing", "1.0", NOBLE)
        text = str(context.exception)
        self.assertIn("не найден в релизе noble", text)
        self.assertIn("не удалось прочитать", text)

    def test_repo_unavailable(self):
        """Недоступный репозиторий: сообщение о недоступности."""
        with self.assertRaises(FetchError) as context:
            load_dependency_source(
                "http://127.0.0.1:1/ubuntu", "nginx", "1.0", NOBLE)
        self.assertIn("недоступен", str(context.exception))


class HelperTests(unittest.TestCase):
    """Вспомогательные функции без сети."""

    def test_pick_version(self):
        """Версия сравнивается строго."""
        entries = [Entry("1.0", ""), Entry("1.0.1", "x")]
        self.assertEqual(pick_version(entries, "1.0.1"), entries[1])
        self.assertIsNone(pick_version(entries, "1"))

    def test_explain_failure_without_failed_indexes(self):
        """Без сбойных индексов приписка не добавляется."""
        text = explain_failure("p", "1", "noble", [], 0)
        self.assertEqual(text, "пакет «p» не найден в релизе noble")


if __name__ == "__main__":
    unittest.main()
