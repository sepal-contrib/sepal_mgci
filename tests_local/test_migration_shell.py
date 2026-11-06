import asyncio
from unittest.mock import patch
import unittest

import ipyvuetify as v
import solara
from pysepal.mapping import SepalMap

from component.solara.app import MgciApp
from component.solara.landcover import LandCoverPanel
from component.solara.session import use_session_state
from mgci.application.state import ResourceState
from mgci.infrastructure.defaults import initial_configuration
from pysepal.solara.notifications import NotificationProvider
from test_solara_components import walk


class MigrationShellTests(unittest.IsolatedAsyncioTestCase):
    async def test_shell_renders_without_authentication_and_keeps_session_on_rerender(self):
        class Interface:
            async def get_folder_async(self):
                return 'projects/test/assets'
        map_ = SepalMap(gee=False, dc=False)
        @solara.component
        def AreaBoundary(*args):
            solara.Text('AOI boundary')
        trigger = solara.reactive(0)
        @solara.component
        def Harness():
            trigger.value
            MgciApp(Interface(), None, object())
        with patch('component.solara.app.SepalMap', return_value=map_), patch('component.solara.app.AreaPanel', AreaBoundary):
            root, context = solara.render(Harness(), handle_error=False)
            try:
                from component.widget.app_shell import MgciMapApp
                shell = next(w for w in walk(root) if isinstance(w, MgciMapApp))
                # The Documentation link opens the published guide, not a file in this repository.
                self.assertEqual(shell.docs_url, 'https://mgci-docs.readthedocs.io/en/latest/sepal/index.html')
                trigger.set(1)
                await asyncio.sleep(.05)
            finally:
                context.close()

    async def test_incomplete_landcover_dialog_can_close_without_becoming_ready(self):
        seen = []
        resources = {key: ResourceState() for key in ('a', 'b', 'transition')}
        @solara.component
        def Harness():
            state, publish = use_session_state(initial_configuration(2026))
            seen.append(state)
            NotificationProvider()
            LandCoverPanel(state, publish, resources, object(), None, None)
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        button = next(w for w in walk(root) if isinstance(w, v.Btn) and 'Set up land cover' in w.children)
        button.fire_event('click', None)
        dialog = next(w for w in walk(root) if isinstance(w, v.Dialog))
        self.assertTrue(dialog.v_model)
        close = next(w for w in walk(root) if isinstance(w, v.Btn) and 'Close' in w.children)
        close.fire_event('click', None)
        self.assertFalse(dialog.v_model)
        from mgci.domain.validation import readiness
        self.assertFalse(readiness(seen[-1].configuration, 'a', 'statistics').ready)


class ToastTimeoutTests(unittest.TestCase):
    def test_errors_persist_until_clicked_and_other_toasts_still_expire(self):
        import component.solara.app  # noqa: F401  (sets the defaults on import)
        from pysepal.solara.notifications import Toast, ToastType
        self.assertIsNone(Toast(message='failed', type=ToastType.ERROR).effective_timeout())
        self.assertEqual(Toast(message='done', type=ToastType.SUCCESS).effective_timeout(), 3.0)
        from component.solara.toasts import LASTING
        self.assertGreater(LASTING, 3.0)


class LandCoverDialogDraftTests(unittest.IsolatedAsyncioTestCase):
    async def render(self):
        from dataclasses import replace
        seen = []
        resources = {key: ResourceState() for key in ('a', 'b', 'transition')}
        @solara.component
        def Harness():
            state, publish = use_session_state(initial_configuration(2026))
            seen.append((state, publish))
            NotificationProvider()
            LandCoverPanel(state, publish, resources, object(), None, None)
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        def press(label):
            next(w for w in walk(root) if isinstance(w, v.Btn) and label in w.children).fire_event('click', None)
        def edit_mapping():
            state, publish = seen[-1]
            state.edit(replace(state.configuration, a=replace(state.configuration.a, mapping=((10, 3),))))
            publish()
        return seen, press, edit_mapping

    async def test_close_restores_the_setup_from_when_the_dialog_opened(self):
        seen, press, edit_mapping = await self.render()
        before = seen[-1][0].configuration.a.mapping
        press('Set up land cover')
        edit_mapping()
        press('Close')
        self.assertEqual(seen[-1][0].configuration.a.mapping, before)

    async def test_reopening_after_close_starts_from_the_saved_setup_again(self):
        seen, press, edit_mapping = await self.render()
        before = seen[-1][0].configuration.a.mapping
        for _ in range(2):
            press('Set up land cover')
            edit_mapping()
            press('Close')
        self.assertEqual(seen[-1][0].configuration.a.mapping, before)
