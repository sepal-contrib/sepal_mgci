import asyncio
import json
from types import SimpleNamespace

from ee.apitestcase import ApiTestCase
import test_science_adapter as fixtures
from mgci.application.state import SessionState
from mgci.infrastructure.tasks import submit, retrieve


class BackgroundAdapterTests(ApiTestCase):
    setUp = fixtures.ScienceAdapterTests.setUp

    def test_submission_persists_snapshot_and_retrieval_keeps_it(self):
        stored = {}
        class Workspace:
            async def mkdir_async(self, path, parents=False):
                pass
            async def write_async(self, path, content, overwrite=False):
                stored[path] = content
            async def read_bytes_async(self, path):
                return stored[path].encode()
        class Interface:
            async def export_table_to_drive_async(self, **kwargs):
                assert kwargs['file_format'] == 'CSV'
                return SimpleNamespace(id='task-1')
            async def get_task_async(self, task_id):
                return SimpleNamespace(metadata=SimpleNamespace(state='COMPLETED'))
        class Drive:
            def download_file(self, filename, output, client):
                client.files.write(output, b'process_id,sub_a\n' + b''.join(f'{year},"[{{biobelt=1, groups=[{{lc=4, sum=3}}]}}]"\n'.encode() for year in (2000, 2015, 2018)))
        async def check():
            request = SessionState(self.config).prepare('a', 'statistics')
            record, path = await submit(request, Interface(), Workspace())
            self.assertEqual(record['task']['id'], 'task-1')
            restored, payload, raw = await retrieve(path, Workspace(), Interface(), Drive())
            self.assertEqual(restored, request)
            self.assertEqual(payload['2000']['sub_a'][0]['groups'][0]['sum'], 3)
            self.assertEqual(json.loads(stored[path])['request']['identity'], request.identity)
        asyncio.run(check())
