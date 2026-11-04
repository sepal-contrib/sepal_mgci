from dataclasses import replace
import unittest

import solara

from component.solara.layers import use_map_layers
from test_report_adapter import report_state


class MapLifecycleTests(unittest.TestCase):
    def test_edit_removes_layer_and_unmount_removes_remaining_layers(self):
        state = report_state()
        original = state.configuration
        trigger = solara.reactive(0)
        installed, removed = [], []
        @solara.component
        def Harness():
            trigger.value
            use_map_layers(state, lambda artifact: installed.append(artifact.request.request_id), removed.append)
        _, context = solara.render(Harness(), handle_error=False)
        request = state.prepare('a', 'layer', state.configuration.a.images[0].asset)
        state.accept(request, {'title': 'Layer'})
        trigger.set(1)
        self.assertEqual(installed, [request.request_id])
        state.edit(replace(state.configuration, aoi_identity='new'))
        trigger.set(2)
        self.assertEqual(removed, [request.request_id])
        state.edit(original)
        request2 = state.prepare('a', 'layer', original.a.images[0].asset)
        state.accept(request2, {'title': 'New layer'})
        trigger.set(3)
        context.close()
        self.assertEqual(removed, [request.request_id, request2.request_id])
