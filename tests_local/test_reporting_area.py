import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import unittest

import ipyvuetify as v
import solara

from component.solara import aoi
from mgci.application.state import ResourceState
from test_solara_components import walk


def render_panel(test, captured, notifier, state):
    @solara.component
    def FakeAoiView(**props):
        captured.update(props)
        props['clear_ref'].current = captured.setdefault('clear', MagicMock())

    for target in (patch.object(aoi, 'AoiView', FakeAoiView), patch.object(aoi, 'use_notifications', return_value=notifier)):
        target.start()
        test.addCleanup(target.stop)
    resources = {key: ResourceState() for key in ('a', 'b', 'transition', 'b_classes')}
    root, context = solara.render(aoi.AreaPanel(state, lambda: None, resources, None, object()), handle_error=False)
    test.addCleanup(context.close)


class AreaPanelTests(unittest.TestCase):
    def setUp(self):
        from mgci.infrastructure.defaults import initial_configuration
        self.state = SimpleNamespace(configuration=initial_configuration(), edit=MagicMock())

    def test_uses_the_pysepal_picker_with_the_reference_methods(self):
        captured, notifier = {}, MagicMock()
        render_panel(self, captured, notifier, self.state)
        self.assertEqual(captured['methods'], ['ADMIN0', 'ADMIN1', 'ADMIN2', 'ASSET'])
        self.assertTrue(captured['gee'])

    def test_reporting_country_is_stored_with_its_m49_code(self):
        captured, notifier = {}, MagicMock()
        render_panel(self, captured, notifier, self.state)
        with patch.object(aoi, 'capture_aoi', return_value=('id', 'graph')):
            captured['on_value'](SimpleNamespace(name='AND', method='ADMIN0', feature_collection=object()))
        config = self.state.edit.call_args.args[0]
        self.assertEqual((config.aoi_name, config.ref_area, config.aoi_identity), ('Andorra', '020', 'id'))
        notifier.error.assert_not_called()

    def test_area_outside_the_reporting_countries_is_rejected(self):
        captured, notifier = {}, MagicMock()
        render_panel(self, captured, notifier, self.state)
        captured['on_value'](SimpleNamespace(name='TWN', method='ADMIN0', feature_collection=object()))
        self.state.edit.assert_not_called()
        notifier.error.assert_called_once()
        self.assertIn('TWN', notifier.error.call_args.args[0])
        captured['clear'].assert_called_once()


class PysepalPickerTests(unittest.IsolatedAsyncioTestCase):
    async def test_offers_only_the_reference_methods(self):
        from pysepal.solara.components.aoi import aoi_view
        from pysepal.solara.notifications import NotificationProvider

        @solara.component
        def Harness():
            NotificationProvider()
            aoi_view.AoiView(methods=aoi.METHODS, gee=True)
        with patch.object(aoi_view, 'get_current_gee_interface'), patch.object(aoi_view.su, 'init_ee'):
            root, context = solara.render(Harness(), handle_error=False)
            self.addCleanup(context.close)
            await asyncio.sleep(0)
        method = next(w for w in walk(root) if isinstance(w, v.Select))
        self.assertEqual([item['value'] for item in method.items if 'value' in item], aoi.METHODS)

    async def test_rejection_follows_the_picker_success_and_clears_it(self):
        from pysepal.solara.components.aoi import aoi_view
        from mgci.infrastructure.defaults import initial_configuration
        calls = []
        notifier = MagicMock()
        notifier.success.side_effect = lambda text: calls.append('success')
        notifier.error.side_effect = lambda text: calls.append('error')
        state = SimpleNamespace(configuration=initial_configuration(), edit=MagicMock())
        resources = {key: ResourceState() for key in ('a', 'b', 'transition', 'b_classes')}
        async def process(**kwargs):
            return SimpleNamespace(name='TWN', method='ADMIN0', feature_collection=None, spec=None)
        with patch.object(aoi_view, 'get_current_gee_interface'), patch.object(aoi_view.su, 'init_ee'), \
             patch.object(aoi_view, 'use_notifications', return_value=notifier), \
             patch.object(aoi, 'use_notifications', return_value=notifier), \
             patch.object(aoi_view, 'process_admin', process):
            root, context = solara.render(aoi.AreaPanel(state, lambda: None, resources, None, object()),
                                          handle_error=False)
            self.addCleanup(context.close)
            next(w for w in walk(root) if isinstance(w, v.Select)).v_model = 'ADMIN0'
            await asyncio.sleep(.05)
            [w for w in walk(root) if isinstance(w, v.Select)][1].v_model = '170'
            await asyncio.sleep(.05)
            next(w for w in walk(root) if isinstance(w, v.Btn) and not w.disabled).fire_event('click', None)
            for _ in range(50):
                if 'error' in calls:
                    break
                await asyncio.sleep(.02)
        self.assertEqual(calls, ['success', 'error'])
        # Only the clear reaches the state, and it empties the AOI.
        self.assertEqual([call.args[0].aoi_name for call in state.edit.call_args_list], [''])
