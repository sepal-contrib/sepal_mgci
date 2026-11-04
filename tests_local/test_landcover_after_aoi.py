import asyncio
from dataclasses import replace
import unittest
from unittest.mock import patch

import ipyvuetify as v
import solara
from pysepal.solara.notifications import NotificationProvider

from component.solara.landcover import LandCoverPanel
from component.solara.session import use_session_state
from mgci.application.state import ResourceState
from mgci.domain.configuration import DatasetDiscovery, DatasetEvidence, ImageSelection
from mgci.domain.validation import readiness
from mgci.infrastructure.defaults import initial_configuration
from test_landcover_parity import widgets, Interface
from test_solara_calculation import until


class LandCoverAfterAreaTests(unittest.IsolatedAsyncioTestCase):
    async def test_setup_after_aoi_publication_inspects_current_area_and_populates_both(self):
        seen, calls = [], []
        resources = {key: ResourceState() for key in ('a', 'b', 'transition')}
        future = asyncio.get_running_loop().create_future()
        async def discover(config, indicator, interface):
            calls.append((config, indicator))
            return await future
        @solara.component
        def Harness():
            state, publish = use_session_state(initial_configuration(2026))
            seen.append((state, publish))
            NotificationProvider()
            LandCoverPanel(state, publish, resources, Interface(), None, None)
        with patch('component.solara.landcover.discover', discover):
            root, context = solara.render(Harness(), handle_error=False)
            self.addCleanup(context.close)
            state, publish = seen[-1]
            state.edit(replace(state.configuration, aoi_identity='new-aoi', aoi_graph='captured'))
            publish()
            button = next(widget for widget in widgets(root) if isinstance(widget, v.Btn)
                          and 'Set up land cover' in widget.children)
            button.fire_event('click', None)
            await until(lambda: bool(calls))
            self.assertEqual(calls[0][0].aoi_identity, 'new-aoi')
            # The class check shows on the asset field's own loading line.
            self.assertTrue(any(isinstance(widget, v.Combobox) and widget.loading for widget in widgets(root)))
            images = tuple(ImageSelection(f'{state.configuration.a.asset}/{year}', year) for year in (2000, 2015, 2018))
            evidence = DatasetEvidence(state.configuration.a.asset, tuple(image.asset for image in images),
                                       (10, 190), 'new-aoi', 'ready')
            future.set_result(DatasetDiscovery(evidence, images))
            await until(lambda: state.configuration.a.evidence is not None)
            self.assertEqual(state.configuration.b.evidence, evidence)
            self.assertTrue(readiness(state.configuration, 'a', 'setup').ready)
            self.assertTrue(readiness(state.configuration, 'b', 'setup').ready)

    async def test_full_mapapp_nested_landcover_uses_published_aoi(self):
        from component.solara.app import MgciApp
        from component.widget.app_shell import MgciMapApp
        from pysepal.mapping import SepalMap
        seen, calls = [], []
        @solara.component
        def AreaPanel(state, publish, *args):
            seen.append((state, publish))
        @solara.component
        def Overlay(*args):
            pass
        async def discover(config, indicator, interface):
            calls.append(config.aoi_identity)
            images = tuple(ImageSelection(f'{config.a.asset}/{year}', year) for year in (2000, 2015, 2018))
            return DatasetDiscovery(DatasetEvidence(config.a.asset, tuple(image.asset for image in images),
                                                    (10, 190), config.aoi_identity, 'ready'), images)
        map_ = SepalMap(gee=False, dc=False)
        with patch('component.solara.app.SepalMap', return_value=map_), patch('component.solara.app.AreaPanel', AreaPanel), \
                patch('component.solara.app.BiobeltOverlay', Overlay), patch('component.solara.landcover.discover', discover):
            root, context = solara.render(MgciApp(Interface(), None, object()), handle_error=False)
            self.addCleanup(context.close)
            def walk_shell(widget):
                yield widget
                for child in getattr(widget, 'children', ()):
                    if not isinstance(child, str):
                        yield from walk_shell(child)
            shell = next(widget for widget in walk_shell(root) if isinstance(widget, MgciMapApp))
            state, publish = seen[-1]
            state.edit(replace(state.configuration, aoi_identity='new-mapapp-aoi', aoi_graph='captured'))
            publish()
            shell.vue_handle_step_activation(3)
            step_content = next(step for step in shell.steps_data if step['id'] == 3)['content']
            button = next(widget for content in step_content for widget in widgets(content)
                          if isinstance(widget, v.Btn) and 'Set up land cover' in widget.children)
            button.fire_event('click', None)
            await until(lambda: bool(calls))
            self.assertEqual(calls, ['new-mapapp-aoi'])
            await until(lambda: state.configuration.a.evidence is not None)
            self.assertTrue(readiness(state.configuration, 'a', 'setup').ready)
            self.assertTrue(readiness(state.configuration, 'b', 'setup').ready)


class DefaultDatasetTests(unittest.IsolatedAsyncioTestCase):
    async def run_after_aoi(self, workflow):
        from mgci.domain.configuration import Workflow
        seen, calls = [], []
        resources = {key: ResourceState() for key in ('a', 'b', 'transition')}
        async def discover(config, indicator, interface):
            calls.append(indicator)
            images = tuple(ImageSelection(f'{config.a.asset}/{year}', year) for year in (2000, 2015, 2018))
            return DatasetDiscovery(DatasetEvidence(config.a.asset, tuple(image.asset for image in images),
                                                    (10, 190), config.aoi_identity, 'ready'), images)
        @solara.component
        def Harness():
            state, publish = use_session_state(replace(initial_configuration(2026), workflow=workflow))
            seen.append((state, publish))
            NotificationProvider()
            LandCoverPanel(state, publish, resources, Interface(), None, None)
        with patch('component.solara.landcover.discover', discover):
            root, context = solara.render(Harness(), handle_error=False)
            self.addCleanup(context.close)
            await asyncio.sleep(.05)
            self.assertEqual(calls, [], 'Nothing to discover before an AOI')
            state, publish = seen[-1]
            state.edit(replace(state.configuration, aoi_identity='aoi', aoi_graph='captured'))
            publish()
            await asyncio.sleep(.1)
        return state, calls

    async def test_default_dataset_is_ready_without_opening_the_dialog(self):
        from mgci.domain.configuration import Workflow
        state, calls = await self.run_after_aoi(Workflow.DEFAULT)
        self.assertTrue(calls)
        self.assertTrue(readiness(state.configuration, 'a', 'statistics').ready)
        self.assertTrue(readiness(state.configuration, 'b', 'statistics').ready)

    async def test_custom_dataset_still_waits_for_get_classes(self):
        from mgci.domain.configuration import Workflow
        state, calls = await self.run_after_aoi(Workflow.CUSTOM_RECLASSIFY)
        self.assertEqual(calls, [])
