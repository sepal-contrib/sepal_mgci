import asyncio
import unittest
from unittest.mock import patch

import solara
from pysepal.mapping import SepalMap

from component.solara.layers import LayerPanel, MapOutputs, use_map_layers
from component.solara.session import use_session_state
from mgci.infrastructure.defaults import initial_configuration
from test_report_adapter import report_state
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


def body_rows(root):
    import ipyvuetify as v
    body = next(w for w in walk(root) if isinstance(w, v.Html) and w.tag == 'tbody')
    return body.children


def layer_rows(root):
    """(title, eye, export) for each row of the table, in order."""
    import ipyvuetify as v
    rows = []
    for row in body_rows(root):
        title, _, actions = row.children
        eye, export = [w for w in walk(actions) if isinstance(w, v.Btn)]
        rows.append((title.children[0], eye, export))
    return rows


def indicator_column(root):
    return [row.children[1].children[0] for row in body_rows(root)]


def eye_icon(eye):
    import ipyvuetify as v
    child = eye.children[0]
    return child.children[0] if isinstance(child, v.Icon) else None


async def until(predicate):
    for _ in range(100):
        if predicate():
            return
        await asyncio.sleep(.01)
    raise AssertionError('Component did not reach expected state')


class FakeController:
    def __init__(self):
        self.selected_source_id = solara.reactive('')
        self.opened = []

    def open_dialog(self):
        self.selected_source_id.value = ''
        self.opened.append(True)


@solara.component
def NoDialog(controller, title):
    pass


class LayerTableTests(unittest.IsolatedAsyncioTestCase):
    def render(self, config, shown=None, enabled=None):
        from pysepal.solara.notifications import NotificationProvider
        shown = shown or solara.reactive(frozenset())
        holder = {}

        @solara.component
        def Harness():
            state, publish = use_session_state(config)
            holder['state'], holder['publish'] = state, publish
            NotificationProvider()
            LayerPanel(state, publish, shown, object(), object(), None, enabled=enabled)

        controller = FakeController()
        for target, value in (('use_export_dialog', lambda *args, **kwargs: controller), ('ExportDialog', NoDialog)):
            patcher = patch(f'component.solara.layers.{target}', value)
            patcher.start()
            self.addCleanup(patcher.stop)
        root, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        self.publish = holder['publish']
        return root, holder['state'], shown, controller

    async def test_switched_off_indicator_offers_no_rows(self):
        enabled = solara.reactive(('a',))
        root, *_ = self.render(initial_configuration(2026), enabled=enabled)
        self.assertEqual(set(indicator_column(root)), {'A'})
        enabled.set(('a', 'b'))
        self.assertEqual(set(indicator_column(root)), {'A', 'B'})

    async def test_unready_rows_are_disabled_and_explain_why_on_hover_only(self):
        import ipyvuetify as v
        # No AOI yet, so no sub-indicator can make layers.
        root, *_ = self.render(initial_configuration(2026))
        self.assertTrue(all(eye.disabled and export.disabled for _, eye, export in layer_rows(root)))
        reasons = [row.children[2].attributes['title'] for row in body_rows(root)]
        self.assertTrue(all(reason.startswith(f'Sub-indicator {letter} is not ready:')
                            for reason, letter in zip(reasons, indicator_column(root))))
        # Every row is a layer: no header or reason rows.
        self.assertTrue(all(len(row.children) == 3 for row in body_rows(root)))
        self.assertFalse([w for w in walk(root) if isinstance(w, v.Alert)])

    async def test_ready_rows_have_no_hover_reason(self):
        root, *_ = self.render(report_state().configuration)
        row = body_rows(root)[0]
        self.assertEqual(indicator_column(root)[0], 'A')
        self.assertNotIn('title', row.children[2].attributes)

    async def test_eye_draws_the_layer_then_hides_and_shows_it_without_earth_engine(self):
        calls = []

        async def prepare_layer(request, gee_interface):
            calls.append(request.slot)
            return {'title': 'Land cover 2000', 'legend': ()}

        with patch('component.solara.layers.prepare_layer', prepare_layer):
            root, state, shown, _ = self.render(report_state().configuration)
            title, eye, _ = layer_rows(root)[0]
            self.assertEqual((title, eye_icon(eye), eye.attributes['aria-label']),
                             ('Land cover 2000', 'mdi-eye-off-outline', 'Show Land cover 2000 on the map'))
            eye.fire_event('click', None)
            await until(lambda: shown.value == {('a', 'lc/2000')})
            self.assertEqual(calls, [('a', 'layer', 'lc/2000')])
            _, eye, _ = layer_rows(root)[0]
            self.assertEqual((eye_icon(eye), eye.attributes['aria-label']), ('mdi-eye', 'Hide Land cover 2000'))
            eye.fire_event('click', None)
            self.assertEqual(shown.value, frozenset())
            self.assertIsNotNone(state.current('a', 'layer', 'lc/2000'))
            layer_rows(root)[0][1].fire_event('click', None)
            self.assertEqual(shown.value, {('a', 'lc/2000')})
            self.assertEqual(len(calls), 1)

    async def test_edit_turns_the_eye_off(self):
        from dataclasses import replace

        async def prepare_layer(request, gee_interface):
            return {'title': 'Land cover 2000', 'legend': ()}

        with patch('component.solara.layers.prepare_layer', prepare_layer):
            root, state, shown, _ = self.render(report_state().configuration)
            layer_rows(root)[0][1].fire_event('click', None)
            await until(lambda: bool(shown.value))
            state.edit(replace(state.configuration, aoi_identity='changed'))
            self.publish()
            self.assertEqual(eye_icon(layer_rows(root)[0][1]), 'mdi-eye-off-outline')

    async def test_running_add_shows_a_cancel_that_stops_it(self):
        pending = asyncio.get_running_loop().create_future()

        async def prepare_layer(request, gee_interface):
            return await pending

        with patch('component.solara.layers.prepare_layer', prepare_layer):
            root, state, shown, _ = self.render(report_state().configuration)
            layer_rows(root)[0][1].fire_event('click', None)
            await until(lambda: eye_icon(layer_rows(root)[0][1]) is None)
            eye = layer_rows(root)[0][1]
            self.assertEqual(eye.attributes['aria-label'], 'Stop adding Land cover 2000')
            eye.fire_event('click', None)
            await until(lambda: eye_icon(layer_rows(root)[0][1]) == 'mdi-eye-off-outline')
            self.assertEqual(shown.value, frozenset())
            self.assertIsNone(state.current('a', 'layer', 'lc/2000'))

    async def test_export_icon_opens_the_dialog_on_its_own_layer(self):
        root, _, _, controller = self.render(report_state().configuration)
        _, _, export = layer_rows(root)[0]
        self.assertFalse(export.disabled)
        self.assertEqual(export.attributes['aria-label'], 'Export Land cover 2000')
        export.fire_event('click', None)
        self.assertEqual((len(controller.opened), controller.selected_source_id.value), (1, 'a|lc/2000'))
        # A second press on the same row opens the dialog again.
        controller.selected_source_id.value = ''
        layer_rows(root)[0][2].fire_event('click', None)
        self.assertEqual((len(controller.opened), controller.selected_source_id.value), (2, 'a|lc/2000'))


class ShownLayersTests(unittest.TestCase):
    def test_only_shown_layers_are_installed(self):
        state = report_state()
        request = state.prepare('a', 'layer', 'lc/2000')
        state.accept(request, {'title': 'Layer'})
        shown = solara.reactive(frozenset())
        installed, removed = [], []

        @solara.component
        def Harness():
            use_map_layers(state, lambda artifact: installed.append(artifact.request.request_id), removed.append,
                           shown.value)

        _, context = solara.render(Harness(), handle_error=False)
        self.addCleanup(context.close)
        self.assertEqual(installed, [])
        shown.set(frozenset({('a', 'lc/2000')}))
        self.assertEqual(installed, [request.request_id])
        shown.set(frozenset())
        self.assertEqual(removed, [request.request_id])
