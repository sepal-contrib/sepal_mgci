import unittest
from types import SimpleNamespace

from mgci.infrastructure.workspace import ClientWorkspace


class WorkspaceTests(unittest.IsolatedAsyncioTestCase):
    async def test_reads_and_writes_only_through_injected_client(self):
        class Files:
            def __init__(self):
                self.content = {'matrix.csv': b'input'}
                self.folders = []
            def read_bytes(self, path):
                return self.content[path]
            def write(self, path, content, overwrite=False):
                if path in self.content and not overwrite:
                    raise FileExistsError(path)
                self.content[path] = content
                return path
            def mkdir(self, path, parents=False):
                self.folders.append(path)
                return path
        client = SimpleNamespace(files=Files())
        workspace = ClientWorkspace(client)
        self.assertEqual(await workspace.read_bytes_async('matrix.csv'), b'input')
        await workspace.mkdir_async('reports', parents=True)
        await workspace.write_async('reports/result.xlsx', b'report')
        self.assertEqual(client.files.content['reports/result.xlsx'], b'report')
        self.assertEqual(client.files.folders, ['reports'])
        self.assertEqual(client.files.content['matrix.csv'], b'input')

    async def test_missing_session_never_falls_back_to_process_files(self):
        with self.assertRaises(ValueError):
            ClientWorkspace(None)
