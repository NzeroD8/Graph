import gzip
import http.server
import os
import sys
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from extract import (  # noqa: E402
    ARCHITECTURE,
    COMPONENTS,
    RELEASE_SUFFIXES,
    FetchError,
    build_index_urls,
    fetch_dependencies,
    pick_version,
)

NGINX = "Package: nginx\nVersion: {v}\nDepends: libc6 (>= 2.34), zlib1g\n\n"
INDEX_FORMAT = "/ubuntu/dists/{}/{}/binary-" + ARCHITECTURE + "/Packages.gz"
NOT_FOUND = 404
NOBLE = "noble"


def route(release, component):
    """Путь файла Packages.gz для пары «релиз, компонент»."""
    return INDEX_FORMAT.format(release, component)


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


class FetcherTests(unittest.TestCase):
    """Получение зависимостей через локальный HTTP-сервер."""

    @classmethod
    def setUpClass(cls):
        """Запускает сервер с индексами двух релизов."""
        routes = {
            route("noble", "main"): gzip.compress(
                NGINX.format(v="1.24.0-2ubuntu7").encode()),
            route("noble-updates", "main"): gzip.compress(
                NGINX.format(v="1.24.0-2ubuntu7.5").encode()),
            route("noble", "universe"): b"not a gzip file",
            route("jammy", "main"): gzip.compress(
                NGINX.format(v="1.18.0-6ubuntu14").encode()),
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
        """Адресов столько, сколько пар «релиз, компонент»."""
        urls = build_index_urls("https://h/ubuntu/", "noble")
        self.assertEqual(len(urls), len(RELEASE_SUFFIXES) * len(COMPONENTS))
        self.assertEqual(urls[0], "https://h/ubuntu/" + route(
            "noble", "main")[len("/ubuntu/"):])
        self.assertIn("dists/noble-security/universe/", urls[-1])

    def test_other_release(self):
        """Релиз берётся из параметра: версия jammy ищется в jammy."""
        deps = fetch_dependencies(
            self.repo, "nginx", "1.18.0-6ubuntu14", "jammy")
        self.assertEqual(deps, ["libc6", "zlib1g"])

    def test_version_of_other_release(self):
        """Версия noble не находится в jammy, релиз назван в ошибке."""
        with self.assertRaises(FetchError) as context:
            fetch_dependencies(
                self.repo, "nginx", "1.24.0-2ubuntu7", "jammy")
        text = str(context.exception)
        self.assertIn("в релизе jammy", text)
        self.assertIn("1.18.0-6ubuntu14", text)
        self.assertNotIn("1.24.0-2ubuntu7.5", text)

    def test_found_in_first_index(self):
        """Версия из основного индекса найдена."""
        deps = fetch_dependencies(
            self.repo, "nginx", "1.24.0-2ubuntu7", NOBLE)
        self.assertEqual(deps, ["libc6", "zlib1g"])

    def test_found_in_updates(self):
        """Версия из другого релиза найдена, битый индекс пропущен."""
        deps = fetch_dependencies(
            self.repo, "nginx", "1.24.0-2ubuntu7.5", NOBLE)
        self.assertEqual(deps, ["libc6", "zlib1g"])

    def test_version_not_found(self):
        """Неизвестная версия: в ошибке перечислены доступные."""
        with self.assertRaises(FetchError) as context:
            fetch_dependencies(self.repo, "nginx", "9.9", NOBLE)
        text = str(context.exception)
        self.assertIn("версия 9.9", text)
        self.assertIn("1.24.0-2ubuntu7.5", text)

    def test_package_not_found(self):
        """Неизвестный пакет."""
        with self.assertRaises(FetchError) as context:
            fetch_dependencies(self.repo, "nothing", "1.0", NOBLE)
        self.assertIn("не найден в релизе noble", str(context.exception))
        self.assertIn("не удалось прочитать", str(context.exception))

    def test_repo_unavailable(self):
        """Недоступный репозиторий: сообщение о недоступности."""
        with self.assertRaises(FetchError) as context:
            fetch_dependencies(
                "http://127.0.0.1:1/ubuntu", "nginx", "1.0", NOBLE)
        self.assertIn("недоступен", str(context.exception))

    def test_pick_version(self):
        """Версия сравнивается строго."""
        records = [{"Version": "1.0"}, {"Version": "1.0.1"}]
        self.assertEqual(pick_version(records, "1.0.1"), records[1])
        self.assertIsNone(pick_version(records, "1"))


if __name__ == "__main__":
    unittest.main()