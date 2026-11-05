import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

import ipyvuetify as v
import solara

from component.solara.settings import CalculationAction
from test_report_adapter import report_state
from test_solara_components import walk
from test_solara_calculation import until


class CalculationFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def check_failure(self, message, workspace, *, stale=False):
        state = report_state()
        attempted, submitted, notices = [], [], []
        async def run(request):
            attempted.append(request)
            if stale:
                state.edit(replace(state.configuration, aoi_identity='changed'))
            raise RuntimeError(message)
        async def submit(request, interface, storage):
            submitted.append(request)
            return {'task': {'id': 'task-1'}}, 'tasks/captured.json'
        notifier = SimpleNamespace(**{kind: lambda message, kind=kind: notices.append((kind, message))
                                      for kind in ('info', 'success', 'error', 'warning')})
        @solara.component
        def Harness():
            CalculationAction(state, lambda: None, ('a',), run, workspace=workspace, gee_interface=object())
        with patch('component.solara.settings.submit', submit), patch('component.solara.settings.use_notifications', return_value=notifier):
            root, context = solara.render(Harness(), handle_error=False)
            self.addCleanup(context.close)
            button = next(w for w in walk(root) if isinstance(w, v.Btn))
            button.fire_event('click', None)
            await until(lambda: bool(attempted) and not button.loading)
        self.assertIsNone(state.current('a', 'statistics'))
        return attempted, submitted, notices

    async def test_ee_limits_submit_the_same_immutable_request_and_explain_retrieval(self):
        for message in ('Computation timed out.', 'User memory limit exceeded.'):
            with self.subTest(message=message):
                attempted, submitted, notices = await self.check_failure(message, object())
                self.assertEqual(submitted, attempted)
                self.assertTrue(any(kind == 'warning' and 'could not be completed on the fly' in text
                                    and 'tasks/captured.json' in text for kind, text in notices))

    async def test_other_failures_and_missing_workspace_do_not_submit(self):
        for message, workspace in (('Asset not found', object()), ('Computation timed out.', None)):
            with self.subTest(message=message, workspace=bool(workspace)):
                _, submitted, notices = await self.check_failure(message, workspace)
                self.assertEqual(submitted, [])
                self.assertIn(('error', message), notices)

    async def test_stale_limit_error_does_not_start_background_work(self):
        _, submitted, notices = await self.check_failure('Computation timed out.', object(), stale=True)
        self.assertEqual(submitted, [])
        self.assertEqual([kind for kind, _ in notices], ['info'])
