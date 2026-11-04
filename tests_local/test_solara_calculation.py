import asyncio
import unittest
from dataclasses import replace

import ipyvuetify as v
import solara
from pysepal.solara.notifications import NotificationProvider

from test_report_adapter import report_state
from test_solara_components import walk
from component.solara.actions import RequestAction


async def until(predicate):
    for _ in range(100):
        if predicate():
            return
        await asyncio.sleep(.01)
    raise AssertionError('Component did not reach expected state')


class CalculationComponentTests(unittest.IsolatedAsyncioTestCase):
    async def test_edit_during_calculation_cannot_publish_stale_result(self):
        state = report_state()
        pending = asyncio.get_running_loop().create_future()
        submitted = []
        async def runner(request):
            submitted.append(request)
            return await pending
        @solara.component
        def Harness():
            NotificationProvider()
            RequestAction(state, lambda: None, 'a', 'statistics', runner, label='Calculate A')
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        button = next(w for w in walk(root) if isinstance(w, v.Btn) and 'Calculate A' in w.children)
        button.fire_event('click', None)
        await until(lambda: bool(submitted))
        state.edit(replace(state.configuration, aoi_identity='changed'))
        pending.set_result({'2000': {'sub_a': []}})
        await until(lambda: not button.loading)
        self.assertIsNone(state.current('a', 'statistics'))
        self.assertEqual(state.history, ())

    async def test_completed_calculation_publishes_artifact_once(self):
        state = report_state()
        async def runner(request):
            return {'2000': {'sub_a': []}}
        @solara.component
        def Harness():
            NotificationProvider()
            RequestAction(state, lambda: None, 'a', 'statistics', runner, label='Calculate A')
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        button = next(w for w in walk(root) if isinstance(w, v.Btn) and 'Calculate A' in w.children)
        button.fire_event('click', None)
        await until(lambda: state.current('a', 'statistics') is not None)
        self.assertEqual(len(state.history), 1)
        self.assertEqual(state.current('a', 'statistics').payload['2000']['sub_a'], ())

    async def test_finished_request_shows_no_success_toast(self):
        from unittest.mock import MagicMock, patch
        state, notifier = report_state(), MagicMock()
        async def runner(request):
            return {'2000': {'sub_a': []}}
        with patch('component.solara.actions.use_notifications', return_value=notifier):
            root, context = solara.render(RequestAction(state, lambda: None, 'a', 'statistics', runner, label='Calculate A'), handle_error=False)
            self.addCleanup(context.close)
            next(w for w in walk(root) if isinstance(w, v.Btn) and 'Calculate A' in w.children).fire_event('click', None)
            await until(lambda: state.current('a', 'statistics') is not None)
            await asyncio.sleep(.05)
        notifier.success.assert_not_called()


class SettingsCalculationTests(unittest.IsolatedAsyncioTestCase):
    async def test_first_calculation_keeps_running_when_the_status_alert_appears(self):
        from unittest.mock import patch
        from component.solara.settings import SettingsPanel
        from mgci.domain.validation import readiness
        state = report_state()
        self.assertTrue(readiness(state.configuration, 'a', 'statistics').ready)
        pending = asyncio.get_running_loop().create_future()
        started, cancelled = [], []
        async def calculate(request, gee_interface):
            started.append(request)
            try:
                return await pending
            except asyncio.CancelledError:
                cancelled.append(request)
                raise
        @solara.component
        def Harness():
            NotificationProvider()
            SettingsPanel(state, lambda: None, object(), None, None, None, enabled=('a',))
        with patch('component.solara.settings.calculate', calculate):
            root, context = solara.render(Harness(), handle_error=False)
            self.addCleanup(context.close)
            button = next(w for w in walk(root) if isinstance(w, v.Btn) and 'Calculate indicator' in str(w.children))
            button.fire_event('click', None)
            await until(lambda: bool(started))
            await asyncio.sleep(.05)
            self.assertEqual(cancelled, [])
            self.assertTrue(any(isinstance(w, v.Alert) for w in walk(root)))
            running = [w for w in walk(root) if isinstance(w, v.Btn) and 'Cancel' in str(w.children)]
            self.assertTrue(running, 'The button must show Cancel while the first calculation runs')
            pending.set_result({'2000': {'sub_a': []}})
            await until(lambda: state.current('a', 'statistics') is not None)
