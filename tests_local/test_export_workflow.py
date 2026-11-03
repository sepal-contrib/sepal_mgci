import asyncio
from dataclasses import replace
import unittest
from unittest.mock import patch

import ipyvuetify as v
import solara
from pysepal.solara.notifications import NotificationProvider

from component.solara.export import LayerExport
from component.solara.session import use_session_state
from test_report_adapter import report_state
from test_solara_components import walk
from test_solara_calculation import until


class ExportWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_export_before_display_prepares_accepted_snapshot_without_installing_layer(self):
        owners, requests = [], []
        async def prepare(request, interface):
            requests.append(request)
            return {'title': 'Land cover 2000', 'scale': 300, 'class_key': '1=Artificial; 4=Trees',
                    'belt_key': '1=Nival', 'export_graph': '{}', 'export_bands': ['lc', 'bioclimatic_belt']}
        @solara.component
        def Harness():
            NotificationProvider()
            state, publish = use_session_state(report_state().configuration)
            owners.append(state)
            LayerExport(state, (), object(), None, None, None, selection=('a', 'lc/2000', 'Land cover 2000'), publish=publish)
        # The source resolver is the separate tested GEE boundary; no export is submitted here.
        from pysepal.solara.components.export import ExportSource, ResolvedExport
        source = lambda state, artifact: ExportSource(artifact.request.request_id, 'Land cover 2000', 'image',
            lambda: ResolvedExport(ee_object=None, default_name='landcover', default_scale=300,
                                   bands=('lc', 'bioclimatic_belt')))
        with patch('component.solara.export.prepare_export', prepare), patch('component.solara.export.export_source', source):
            root, context = solara.render(Harness(), handle_error=False)
            self.addCleanup(context.close)
            button = next(w for w in walk(root) if isinstance(w, v.Btn) and 'Export layer' in w.children)
            self.assertFalse(button.disabled)
            button.fire_event('click', None)
            await until(lambda: owners[-1].current('a', 'image_export', 'lc/2000') is not None)
            await until(lambda: any(isinstance(w, v.Dialog) and w.v_model for w in walk(root)))
            self.assertEqual(requests[0].slot, ('a', 'image_export', 'lc/2000'))
            self.assertIsNone(owners[-1].current('a', 'layer', 'lc/2000'))

    async def test_edit_during_export_preparation_cannot_open_stale_dialog(self):
        owners, requests = [], []
        pending = asyncio.get_running_loop().create_future()
        async def prepare(request, interface):
            requests.append(request)
            return await pending
        @solara.component
        def Harness():
            NotificationProvider()
            state, publish = use_session_state(report_state().configuration)
            owners.append((state, publish))
            LayerExport(state, (), object(), None, None, None, selection=('a', 'lc/2000', 'Land cover 2000'), publish=publish)
        with patch('component.solara.export.prepare_export', prepare):
            root, context = solara.render(Harness(), handle_error=False)
            self.addCleanup(context.close)
            button = next(w for w in walk(root) if isinstance(w, v.Btn) and 'Export layer' in w.children)
            button.fire_event('click', None)
            await until(lambda: bool(requests))
            state, publish = owners[-1]
            state.edit(replace(state.configuration, aoi_identity='different'))
            publish()
            pending.set_result({'title': 'old'})
            await until(lambda: not button.loading)
            self.assertIsNone(state.current('a', 'image_export', 'lc/2000'))
            self.assertFalse(any(isinstance(w, v.Dialog) and w.v_model for w in walk(root)))
