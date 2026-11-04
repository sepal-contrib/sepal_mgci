import unittest

import solara
from pysepal.mapping import SepalMap

from component.solara.layers import MapOutputs
from component.solara.session import use_session_state
from mgci.infrastructure.defaults import initial_configuration
from test_solara_components import walk


class MapOutputsTests(unittest.TestCase):
    def test_context_legend_renders_without_the_results_panel(self):
        legend = {'items': [{'label': 'Alpine', 'color': '#ffd700'}]}

        @solara.component
        def Harness():
            state, _ = use_session_state(initial_configuration(2026))
            MapOutputs(state, SepalMap(gee=False, dc=False), legend)

        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        widget = next(w for w in walk(root) if w.has_trait('legend_data'))
        self.assertTrue(widget.visible)
        self.assertEqual(widget.legend_data, legend)
        self.assertEqual(widget.selected, 'biobelts')


class LayerChoicesTests(unittest.IsolatedAsyncioTestCase):
    async def test_switched_off_indicator_offers_no_layers(self):
        import ipyvuetify as v
        from pysepal.solara.notifications import NotificationProvider
        from component.solara.layers import LayerPanel
        enabled = solara.reactive(('a',))

        @solara.component
        def Harness():
            state, publish = use_session_state(initial_configuration(2026))
            NotificationProvider()
            LayerPanel(state, publish, SepalMap(gee=False, dc=False), object(), object(), None, enabled=enabled)

        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        def values():
            select = next(w for w in walk(root) if isinstance(w, v.Select))
            return [item.get('value', '') for item in select.items if 'value' in item]
        self.assertTrue(values())
        self.assertTrue(all(value.startswith('a:') for value in values()))
        enabled.set(('a', 'b'))
        self.assertTrue(any(value.startswith('b:') for value in values()))

    async def test_unready_layer_explains_itself_in_a_hint_not_an_alert(self):
        import ipyvuetify as v
        from pysepal.solara.notifications import NotificationProvider
        from component.solara.layers import LayerPanel

        @solara.component
        def Harness():
            # No AOI yet, so sub-indicator A cannot make layers.
            state, publish = use_session_state(initial_configuration(2026))
            NotificationProvider()
            LayerPanel(state, publish, SepalMap(gee=False, dc=False), object(), object(), None)

        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        select = next(w for w in walk(root) if isinstance(w, v.Select))
        self.assertEqual(select.hint, '')
        select.v_model = next(item['value'] for item in select.items if item.get('value', '').startswith('a:'))
        select = next(w for w in walk(root) if isinstance(w, v.Select))
        self.assertTrue(select.hint.startswith('Sub-indicator A is not ready:'))
        self.assertTrue(select.persistent_hint)
        self.assertFalse([w for w in walk(root) if isinstance(w, v.Alert)])
