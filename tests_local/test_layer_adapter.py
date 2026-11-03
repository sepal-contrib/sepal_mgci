import asyncio
from dataclasses import replace
import json
from types import SimpleNamespace

import ee

from ee.apitestcase import ApiTestCase
import test_science_adapter as fixtures
from mgci.application.state import SessionState
from mgci.infrastructure.layers import prepare_layer, export_source


class LayerAdapterTests(ApiTestCase):
    setUp = fixtures.ScienceAdapterTests.setUp

    def test_layer_export_uses_exact_accepted_graph_and_rejects_stale_source(self):
        state = SessionState(self.config)
        request = state.prepare('a', 'layer', 'lc/2000')
        class Interface:
            async def get_info_async(self, graph):
                return {'scale': 300, 'projection': {'crs': 'EPSG:4326'}, 'bands': ['remapped'],
                        'bounds': [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]}
            async def get_map_id_async(self, graph, params):
                return {'tile_fetcher': SimpleNamespace(url_format='https://tiles.test/{z}/{x}/{y}')}
        payload = asyncio.run(prepare_layer(request, Interface()))
        self.assertTrue(state.accept(request, payload))
        source = export_source(state, state.current('a', 'layer', 'lc/2000'))
        resolved = source.resolve()
        self.assertEqual(json.loads(resolved.ee_object.serialize()), json.loads(payload['export_graph']))
        self.assertEqual(resolved.default_scale, 300)
        state.edit(replace(self.config, aoi_identity='changed'))
        with self.assertRaises(ValueError):
            source.resolve()

    def test_export_restores_belt_band_and_class_metadata_from_snapshot(self):
        from mgci.infrastructure.layers import prepare_export
        from mgci.infrastructure.science import build_layer
        state = SessionState(self.config)
        request = state.prepare('a', 'image_export', 'lc/2000')
        class Interface:
            async def get_info_async(self, graph):
                return {'scale': 300, 'projection': {'crs': 'EPSG:4326'}, 'bands': ['remapped']}
        payload = asyncio.run(prepare_export(request, Interface()))
        self.assertNotIn('url', payload)
        state.accept(request, payload)
        resolved = export_source(state, state.current(*request.slot)).resolve()
        layer = build_layer(request)
        belt = ee.Image(self.config.biobelt).rename('bioclimatic_belt').clip(self.aoi).updateMask(layer.mask()).toInt16()
        expected = layer.toInt16().addBands(belt).set({
            'mgci_pixel_classes': payload['class_key'],
            'mgci_bioclimatic_belt_classes': payload['belt_key'],
        })
        expected = ee.deserializer.decode(json.loads(expected.serialize()))
        self.assertEqual(resolved.ee_object.serialize(), expected.serialize())
        self.assertEqual(resolved.bands, ('remapped', 'bioclimatic_belt'))
        self.assertEqual(resolved.default_name, 'SubA_landcover2000')
        self.assertEqual(resolved.gee_folder, f'sepal_sdg15_4_2/{self.config.aoi_label}_{state.session_id}')
        self.assertEqual(resolved.default_scale, 300)
        self.assertIn('1=Nival', payload['belt_key'])
        self.assertIn('1=', payload['class_key'])
        self.assertEqual(payload['scale'], 300)
        self.assertIsNone(state.current('a', 'layer', 'lc/2000'))

    def test_b_has_report_degradation_and_land_cover_choices(self):
        from mgci.infrastructure.science import build_layer
        state = SessionState(self.config)
        for selector in ('lc/2018|report_degradation', 'lc/2000|land_cover', 'lc/2015|land_cover'):
            with self.subTest(selector=selector):
                self.assertIsInstance(build_layer(state.prepare('b', 'layer', selector)), ee.Image)

    def test_layer_install_recenters_to_captured_aoi_bounds(self):
        from component.solara.layers import install_layer
        state = SessionState(self.config)
        request = state.prepare('a', 'layer', 'lc/2000')
        class Interface:
            async def get_info_async(self, graph):
                return {'scale': 300, 'projection': {'crs': 'EPSG:4326'}, 'bands': ['remapped'],
                        'bounds': [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]}
            async def get_map_id_async(self, graph, params):
                return {'tile_fetcher': SimpleNamespace(url_format='https://tiles.test/{z}/{x}/{y}')}
        class Map:
            def __init__(self):
                self.layers, self.bounds = [], []
            def add_layer(self, layer, key):
                self.layers.append((key, layer))
            def zoom_bounds(self, bounds):
                self.bounds.append(bounds)
        payload = asyncio.run(prepare_layer(request, Interface()))
        state.accept(request, payload)
        map_ = Map()
        install_layer(map_, state.current(*request.slot))
        self.addCleanup(map_.layers[0][1].close)
        self.assertEqual(map_.bounds, [(0, 0, 1, 1)])
