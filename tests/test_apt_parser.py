import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from apt_parser import (  # noqa: E402
    direct_dependencies,
    extract_name,
    find_records,
    iter_records,
    parse_dependencies,
    parse_record,
)

SAMPLE = """Package: nginx
Version: 1.24.0-2ubuntu7
Pre-Depends: init-system-helpers (>= 1.54~)
Depends: libc6 (>= 2.34), libssl3 (>= 3.0.0),
 nginx-common (= 1.24.0-2ubuntu7) | nginx-core
Description: small, powerful web server
 Nginx is a web server.
 .
 More text, with: colons.

Package: libc6
Version: 2.39-0ubuntu8
Depends: libgcc-s1, python3:any [amd64], foo <!nocheck>

Package: empty
Version: 1
"""


class ParseRecordTests(unittest.TestCase):
    """Разбор отдельной записи и потока записей."""

    def test_fields_and_continuation(self):
        """Многострочные значения склеиваются через перевод строки."""
        record = parse_record(SAMPLE.split("\n\n")[0].splitlines())
        self.assertEqual(record["Package"], "nginx")
        self.assertIn("nginx-core", record["Depends"])
        self.assertIn("More text, with: colons.", record["Description"])

    def test_iter_records_count(self):
        """Записи разделяются пустыми строками, хвост без пустой строки тоже."""
        records = list(iter_records(SAMPLE.splitlines(keepends=True)))
        self.assertEqual([r["Package"] for r in records],
                         ["nginx", "libc6", "empty"])

    def test_find_records(self):
        """Поиск возвращает только записи с нужным именем."""
        lines = SAMPLE.splitlines()
        self.assertEqual(len(find_records(lines, "libc6")), 1)
        self.assertEqual(find_records(lines, "nothing"), [])

    def test_no_separator_line_ignored(self):
        """Строка без двоеточия не ломает разбор."""
        self.assertEqual(parse_record(["garbage", "A: b"]), {"A": "b"})


class DependencyTests(unittest.TestCase):
    """Разбор полей зависимостей."""

    def test_extract_name(self):
        """Версия, архитектура и условия отбрасываются."""
        cases = {
            "libc6 (>= 2.34)": "libc6",
            " python3:any [amd64]": "python3",
            "foo <!nocheck>": "foo",
            "g++-13": "g++-13",
            "": "",
            "(>= 1)": "",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(extract_name(text), expected)

    def test_alternatives_and_duplicates(self):
        """Альтернативы попадают в список, повторы убираются."""
        value = "a (>= 1), b | c, a, d:any"
        self.assertEqual(parse_dependencies(value), ["a", "b", "c", "d"])

    def test_empty_value(self):
        """Пустое значение даёт пустой список."""
        self.assertEqual(parse_dependencies(""), [])

    def test_direct_dependencies_order(self):
        """Pre-Depends идут перед Depends."""
        record = list(iter_records(SAMPLE.splitlines()))[0]
        self.assertEqual(
            direct_dependencies(record),
            ["init-system-helpers", "libc6", "libssl3",
             "nginx-common", "nginx-core"],
        )

    def test_no_dependency_fields(self):
        """Запись без зависимостей даёт пустой список."""
        self.assertEqual(direct_dependencies({"Package": "x"}), [])


if __name__ == "__main__":
    unittest.main()