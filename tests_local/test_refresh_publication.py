import asyncio
from dataclasses import dataclass, replace
from unittest.mock import patch
import unittest

import ipyvuetify as v
import solara
from pysepal.solara.notifications import NotificationProvider

from component.solara.landcover import DatasetEditor
from component.solara.layers import use_map_layers
from component.solara.export import LayerExport
from mgci.application.state import ResourceState
from mgci.domain.configuration import DatasetDiscovery
from test_report_adapter import report_state
from test_solara_components import walk
from test_solara_calculation import until


class RefreshPublicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_discovery_removes_old_map_output_before_remote_response(self):
        state = report_state()
        captured = state.configuration.a
        request = state.prepare('a', 'layer', captured.images[0].asset)
        state.accept(request, {})
        future = asyncio.get_running_loop().create_future()
        started = []
        async def discover(*args):
            started.append(True)
            return await future
        trigger = solara.reactive(0)
        removed = []
        def publish():
            trigger.set(trigger.value + 1)
        @solara.component
        def Harness():
            trigger.value
            NotificationProvider()
            use_map_layers(state, lambda artifact: None, removed.append)
            DatasetEditor(state, publish, 'a', resource, object())
        resource = ResourceState()
        with patch('component.solara.landcover.discover', discover):
            root, context = solara.render(Harness(), handle_error=False)
            self.addCleanup(context.close)
            button = next(w for w in walk(root) if isinstance(w, v.Btn) and 'Get classes' in w.children)
            button.fire_event('click', None)
            await until(lambda: bool(started))
            self.assertEqual(removed, [request.request_id])
            self.assertIsNone(state.configuration.a.evidence)
            future.set_result(DatasetDiscovery(captured.evidence, captured.images))
            await until(lambda: resource.status == 'ready')
            self.assertIsNone(state.current('a', 'layer', captured.images[0].asset))

    async def test_export_submission_waits_for_refresh_and_refuses_invalidated_artifact(self):
        state = report_state()
        request = state.prepare('a', 'layer', state.configuration.a.images[0].asset)
        state.accept(request, {'title': 'Layer'})
        artifact = state.current(*request.slot)
        submitted, controllers, refreshed = [], [], []
        @dataclass
        class Controller:
            selected_source_id: object
            submit_export: object
            open_dialog: object
        controller = Controller(solara.reactive(request.request_id), lambda: submitted.append(True), lambda: None)
        @solara.component
        def Dialog(controller, artifact, submit, checking, cancel):
            controllers.append(submit)
        async def before_use(artifacts):
            self.assertEqual(artifacts, (artifact,))
            state.edit(replace(state.configuration, aoi_identity='changed'))
            refreshed.append(True)
        @solara.component
        def Harness():
            NotificationProvider()
            LayerExport(state, (artifact,), object(), object(), None, before_use)
        with patch('component.solara.export.use_export_dialog', return_value=controller), patch('component.solara.export.ExportMapDialog', Dialog):
            _, context = solara.render(Harness(), handle_error=False)
            self.addCleanup(context.close)
            controllers[-1]()
            await until(lambda: bool(refreshed))
            await asyncio.sleep(.02)
            self.assertEqual(submitted, [])
