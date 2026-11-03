import asyncio
import json
from types import SimpleNamespace

from ee.apitestcase import ApiTestCase
import test_science_adapter as fixtures
from mgci.application.state import SessionState
from mgci.infrastructure.tasks import submit


class SubmissionCancellationTests(ApiTestCase):
    setUp = fixtures.ScienceAdapterTests.setUp

    def test_cancel_during_submission_or_record_write_preserves_task_id(self):
        async def check(phase):
            reached, release = asyncio.Event(), asyncio.Event()
            stored = {}
            class Workspace:
                async def mkdir_async(self, *args, **kwargs):
                    pass
                async def write_async(self, path, content, overwrite=False):
                    if overwrite and phase == 'record':
                        reached.set()
                        await release.wait()
                    stored[path] = json.loads(content)
            class Interface:
                async def export_table_to_drive_async(self, **kwargs):
                    if phase == 'submission':
                        reached.set()
                        await release.wait()
                    return SimpleNamespace(id='submitted-1')
            request = SessionState(self.config).prepare('a', 'statistics')
            pending = asyncio.create_task(submit(request, Interface(), Workspace()))
            await reached.wait()
            pending.cancel()
            await asyncio.sleep(0)
            pending.cancel()
            await asyncio.sleep(0)
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await pending
            record, = stored.values()
            self.assertEqual(record['task'], {'id': 'submitted-1', 'name': f'SDG1542_{request.request_id}'})
            self.assertEqual(record['request']['identity'], request.identity)
        for phase in ('submission', 'record'):
            with self.subTest(phase=phase):
                asyncio.run(check(phase))
