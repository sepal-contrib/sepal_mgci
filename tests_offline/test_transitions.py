import unittest
from dataclasses import replace

from test_domain import configuration
from mgci.domain.validation import readiness
from mgci.domain.provenance import scientific_identity
from mgci.infrastructure.transitions import load_transition, parse_transition

CSV = b'from_code,to_code,impact_code\n1,1,2\n1,2,1\n2,1,3\n2,2,2\n'


class TransitionTests(unittest.TestCase):
    def test_normalizes_strings_and_keeps_content_identity(self):
        table = parse_transition(CSV, 'selected.csv')
        self.assertEqual(table.rows, ((1, 1, 2), (1, 2, 1), (2, 1, 3), (2, 2, 2)))
        self.assertTrue(table.explicitly_selected)
        self.assertTrue(readiness(replace(configuration(), transition=table), 'b', 'statistics').ready)
        decimal = parse_transition(CSV.replace(b'1,1,2', b'1.0,1,2'), 'selected.csv')
        self.assertEqual(decimal.rows, table.rows)
        self.assertNotEqual(decimal.content_digest, table.content_digest)

    def test_same_path_rewrite_changes_b_identity(self):
        old = replace(configuration(), transition=parse_transition(CSV, 'selected.csv'))
        new = replace(old, transition=parse_transition(CSV.replace(b'1,2,1', b'1,2,3'), 'selected.csv'))
        self.assertNotEqual(scientific_identity(old, 'b', 'statistics'),
                            scientific_identity(new, 'b', 'statistics'))

    def test_bad_headers_duplicate_normalized_pairs_and_invalid_values(self):
        for content in (b'from_code,to_code\n1,2\n',
                        b'from_code,to_code,impact_code,impact_code\n1,2,2,3\n',
                        CSV + b'1.0,1,2\n',
                        CSV.replace(b'1,1,2', b'1.1,1,2'),
                        CSV.replace(b'1,1,2', b'1,1,4'),
                        CSV.replace(b'1,1,2', b'1,1,'),
                        CSV.replace(b'1,1,2', b'1,1,2,excess'), b'\xff'):
            with self.subTest(content=content), self.assertRaises(ValueError):
                parse_transition(content, 'selected.csv')

    def test_derived_column_is_not_required_or_trusted(self):
        table = parse_transition(b'from_code,to_code,impact_code,transition\n1,1,2,9999\n', 'x.csv')
        self.assertEqual(table.rows, ((1, 1, 2),))


class FileTests(unittest.IsolatedAsyncioTestCase):
    async def test_remote_bytes_read_once_without_writing_input(self):
        class Files:
            def __init__(self):
                self.reads = []
            async def read_bytes_async(self, path):
                self.reads.append(path)
                return CSV
        files = Files()
        table = await load_transition(files, 'module_results/transitions.csv')
        self.assertEqual(files.reads, ['module_results/transitions.csv'])
        self.assertEqual(table.rows[1], (1, 2, 1))

    async def test_inaccessible_and_invalid_file_remain_distinct(self):
        class Missing:
            async def read_bytes_async(self, path):
                raise OSError('Unavailable workspace')
        with self.assertRaises(OSError):
            await load_transition(Missing(), 'module_results/missing.csv')
        class Invalid:
            async def read_bytes_async(self, path):
                return b'invalid'
        with self.assertRaises(ValueError):
            await load_transition(Invalid(), 'module_results/invalid.csv')


class NewlineTests(unittest.TestCase):
    def test_csv_accepts_packaged_cr_and_windows_crlf_line_endings(self):
        for newline in (b'\r', b'\r\n'):
            with self.subTest(newline=newline):
                table = parse_transition(CSV.replace(b'\n', newline), 'selected.csv')
                self.assertEqual(table.rows, ((1, 1, 2), (1, 2, 1), (2, 1, 3), (2, 2, 2)))
