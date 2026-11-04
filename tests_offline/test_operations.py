import asyncio
import unittest
from dataclasses import replace

from test_domain import configuration
from test_transitions import CSV
from mgci.application.state import SessionState, ResourceState
from mgci.application.operations import select_transition
from mgci.infrastructure.transitions import load_transition


class TransitionOperationTests(unittest.IsolatedAsyncioTestCase):
    async def test_read_completion_cannot_restore_file_after_b_edit_away_and_back(self):
        future = asyncio.get_running_loop().create_future()
        class Files:
            async def read_bytes_async(self, path):
                return await future
        state, resource = SessionState(configuration()), ResourceState()
        task = asyncio.create_task(select_transition(state, resource, lambda path: load_transition(Files(), path), 'selected.csv'))
        await asyncio.sleep(0)
        self.assertIsNone(state.configuration.transition)
        draft = state.configuration
        state.edit(replace(draft, b=replace(draft.b, mapping=((10, 2), (20, 1)))))
        state.edit(draft)
        future.set_result(CSV)
        self.assertFalse(await task)
        self.assertIsNone(state.configuration.transition)
        self.assertNotEqual(resource.status, 'loading')

    async def test_old_error_does_not_clear_new_file(self):
        future = asyncio.get_running_loop().create_future()
        class Files:
            async def read_bytes_async(self, path):
                if path == 'old.csv':
                    return await future
                return CSV
        state, resource = SessionState(configuration()), ResourceState()
        old = asyncio.create_task(select_transition(state, resource, lambda path: load_transition(Files(), path), 'old.csv'))
        await asyncio.sleep(0)
        self.assertTrue(await select_transition(state, resource, lambda path: load_transition(Files(), path), 'new.csv'))
        future.set_exception(OSError('old failure'))
        self.assertFalse(await old)
        self.assertEqual(state.configuration.transition.source, 'new.csv')
        self.assertEqual(resource.status, 'ready')

    async def test_a_edit_during_read_does_not_block_b(self):
        state, resource = SessionState(configuration()), ResourceState()
        class Files:
            async def read_bytes_async(self, path):
                state.edit(replace(state.configuration, a=replace(state.configuration.a, mapping=((10, 2), (20, 1)))))
                return CSV
        self.assertTrue(await select_transition(state, resource, lambda path: load_transition(Files(), path), 'selected.csv'))
        self.assertTrue(state.configuration.transition.explicitly_selected)

    async def test_clear_does_not_read_and_revokes_b_readiness(self):
        state, resource = SessionState(configuration()), ResourceState()
        self.assertFalse(await select_transition(state, resource, object(), ''))
        self.assertIsNone(state.configuration.transition)
        self.assertEqual(resource.status, 'empty')


class RefreshTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_bytes_preserve_current_result_but_changed_bytes_clear_it(self):
        from mgci.application.operations import refresh_transition
        from mgci.infrastructure.transitions import parse_transition
        state = SessionState(replace(configuration(), transition=parse_transition(CSV, 'selected.csv')))
        resource = ResourceState()
        request = state.prepare('b', 'statistics')
        state.accept(request, {'area': 1})
        async def same(path):
            return parse_transition(CSV, path)
        self.assertTrue(await refresh_transition(state, same))
        self.assertIsNotNone(state.current('b', 'statistics'))
        async def changed(path):
            return parse_transition(CSV.replace(b'1,2,1', b'1,2,3'), path)
        self.assertTrue(await refresh_transition(state, changed))
        self.assertIsNone(state.current('b', 'statistics'))

    async def test_disposed_session_rejects_pending_file_result(self):
        from mgci.infrastructure.transitions import parse_transition
        state, resource = SessionState(configuration()), ResourceState()
        async def load(path):
            state.close()
            return parse_transition(CSV, path)
        self.assertFalse(await select_transition(state, resource, load, 'selected.csv'))


class ExecutionPreparationTests(unittest.IsolatedAsyncioTestCase):
    async def test_b_refreshes_same_path_before_capturing_request(self):
        from mgci.application.operations import prepare_request
        from mgci.infrastructure.transitions import parse_transition
        state, resource = SessionState(configuration()), ResourceState()
        changed = parse_transition(CSV.replace(b'1,2,1', b'1,2,3'), 'matrix.csv')
        async def load(path):
            self.assertEqual(path, 'matrix.csv')
            return changed
        request = await prepare_request(state, 'b', 'statistics', load=load)
        self.assertEqual(request.configuration.transition, changed)

    async def test_failed_refresh_refuses_execution_but_keeps_file_and_results(self):
        from mgci.application.operations import prepare_request
        state, resource = SessionState(configuration()), ResourceState()
        table = state.configuration.transition
        accepted = state.prepare('b', 'statistics')
        state.accept(accepted, {'area': 1})
        async def load(path):
            raise OSError('File removed')
        with self.assertRaises(OSError):
            await prepare_request(state, 'b', 'layer', load=load)
        self.assertEqual(state.configuration.transition, table)
        self.assertIsNotNone(state.current('b', 'statistics'))
        self.assertEqual(resource.status, 'empty')

    async def test_concurrent_refreshes_both_succeed(self):
        from mgci.application.operations import refresh_transition
        state = SessionState(configuration())
        table = state.configuration.transition
        async def load(path):
            await asyncio.sleep(0)
            return table
        self.assertEqual(await asyncio.gather(refresh_transition(state, load), refresh_transition(state, load)),
                         [True, True])

    async def test_refresh_rejects_edit_during_read(self):
        from mgci.application.operations import refresh_transition
        state = SessionState(configuration())
        table = state.configuration.transition
        async def load(path):
            state.edit(replace(state.configuration, b=replace(state.configuration.b, images=())))
            return table
        with self.assertRaises(ValueError):
            await refresh_transition(state, load)

    async def test_not_ready_carries_issue_codes(self):
        from mgci.domain.validation import NotReady
        state = SessionState(replace(configuration(), aoi_identity=''))
        with self.assertRaises(NotReady) as raised:
            state.prepare('a', 'statistics')
        self.assertIn('aoi_required', [issue.code for issue in raised.exception.issues])

    async def test_a_does_not_need_b_workspace_file(self):
        from mgci.application.operations import prepare_request
        state = SessionState(configuration())
        request = await prepare_request(state, 'a', 'statistics')
        self.assertEqual(request.slot[0], 'a')
