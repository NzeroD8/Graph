import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from apt_parser import (  # noqa: E402
    INDEX_FIELDS,
    Entry,
    collect_entries,
    dependencies_text,
    extract_name,
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

    def test_only_wanted_fields(self):
        """Лишние поля и их продолжения отбрасываются."""
        record = parse_record(
            SAMPLE.split("\n\n")[0].splitlines(), INDEX_FIELDS)
        self.assertNotIn("Description", record)
        self.assertEqual(
            sorted(record),
            ["Depends", "Package", "Pre-Depends", "Version"])
        self.assertTrue(record["Depends"].endswith("nginx-core"))

    def test_iter_records_count(self):
        """Записи разделяются пустыми строками, хвост без пустой строки тоже."""
        records = list(iter_records(SAMPLE.splitlines(keepends=True)))
        self.assertEqual([r["Package"] for r in records],
                         ["nginx", "libc6", "empty"])

    def test_no_separator_line_ignored(self):
        """Строка без двоеточия не ломает разбор."""
        self.assertEqual(parse_record(["garbage", "A: b"]), {"A": "b"})


class EntryTests(unittest.TestCase):
    """Сбор записей индекса."""

    def test_collect_entries(self):
        """Для каждого пакета сохраняются версия и текст зависимостей."""
        entries = collect_entries(SAMPLE.splitlines(keepends=True))
        self.assertEqual(sorted(entries), ["empty", "libc6", "nginx"])
        nginx = entries["nginx"][0]
        self.assertIsInstance(nginx, Entry)
        self.assertEqual(nginx.version, "1.24.0-2ubuntu7")
        self.assertTrue(nginx.dependencies.startswith("init-system-helpers"))
        self.assertEqual(entries["empty"], [Entry("1", "")])

    def test_several_versions_kept(self):
        """Несколько версий одного пакета в индексе не теряются."""
        text = "Package: a\nVersion: 1\n\nPackage: a\nVersion: 2\n"
        entries = collect_entries(text.splitlines())
        self.assertEqual([e.version for e in entries["a"]], ["1", "2"])

    def test_record_without_version_skipped(self):
        """Запись без версии не попадает в индекс."""
        self.assertEqual(collect_entries(["Package: a"]), {})

    def test_dependencies_text_order(self):
        """Pre-Depends идут перед Depends."""
        record = {"Depends": "b", "Pre-Depends": "a"}
        self.assertEqual(dependencies_text(record), "a, b")
        self.assertEqual(dependencies_text({}), "")


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

    def test_full_entry(self):
        """Полный путь: запись -> текст -> имена зависимостей."""
        entries = collect_entries(SAMPLE.splitlines(keepends=True))
        self.assertEqual(
            parse_dependencies(entries["nginx"][0].dependencies),
            ["init-system-helpers", "libc6", "libssl3",
             "nginx-common", "nginx-core"],
        )


if __name__ == "__main__":
    unittest.main()
