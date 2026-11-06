import asyncio
from dataclasses import replace
import json
from types import SimpleNamespace

import ee

from ee.apitestcase import ApiTestCase
import test_science_adapter as fixtures
from mgci.application.state import SessionState
from mgci.infrastructure.layers import export_sources, prepare_layer


class LayerAdapterTests(ApiTestCase):
    setUp = fixtures.ScienceAdapterTests.setUp

    def test_layer_payload_keeps_map_and_legend_data(self):
        state = SessionState(self.config)
        request = state.prepare('a', 'layer', 'lc/2000')
        class Interface:
            async def get_info_async(self, graph):
                return {'scale': 300, 'bands': ['remapped'], 'bounds': [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]}
            async def get_map_id_async(self, graph, params):
                return {'tile_fetcher': SimpleNamespace(url_format='https://tiles.test/{z}/{x}/{y}')}
        payload = asyncio.run(prepare_layer(request, Interface()))
        self.assertTrue(state.accept(request, payload))
        self.assertEqual(payload['url'], 'https://tiles.test/{z}/{x}/{y}')
        self.assertEqual(payload['title'], 'Land cover 2000')
        self.assertIn('1=Nival', payload['belt_key'])

    def test_export_sources_build_the_image_from_current_settings(self):
        from mgci.infrastructure.science import build_layer
        from mgci.application.state import Request
        from mgci.domain.provenance import scientific_identity
        sources = export_sources(self.config, ('a', 'b'), 1234)
        source = next(source for source in sources if source.id == 'a|lc/2000')
        self.assertEqual((source.label, source.kind, source.disabled),
                         ('Land cover 2000 (Sub indicator A)', 'image', False))
        resolved = source.resolve()
        graph = resolved.ee_object.serialize()
        # Band 1 is the layer, band 2 the bioclimatic belt, with both class keys as properties.
        for expected in ('Image.addBands', 'bioclimatic_belt', 'mgci_pixel_classes', 'mgci_bioclimatic_belt_classes'):
            self.assertIn(expected, graph)
        self.assertEqual(resolved.default_name, 'SubA_landcover2000')
        self.assertEqual(resolved.gee_folder, f'sepal_sdg15_4_2/{self.config.aoi_label}_1234')
        self.assertEqual(resolved.default_scale, self.config.scale.metres or 1000)

    def test_french_titles_keep_english_export_names_and_metadata(self):
        from pysepal.i18n import set_locale
        set_locale('fr')
        self.addCleanup(set_locale, 'en')
        sources = {source.id: source for source in export_sources(self.config, ('a', 'b'), 1)}
        self.assertEqual(sources['a|lc/2000'].label, 'Couverture terrestre 2000 (Sous-indicateur A)')
        self.assertEqual(sources['a|lc/2000'].resolve().default_name, 'SubA_landcover2000')
        degradation = next(source for key, source in sources.items() if key.endswith('|final_degradation'))
        resolved = degradation.resolve()
        self.assertRegex(resolved.default_name, r'^SubB_totaldegradation\d{4}$')
        self.assertEqual(resolved.vis_params['labels'], ['Dégradé', 'Stable', 'Amélioré'])
        self.assertIn('1=Degraded', resolved.ee_object.serialize())

    def test_belts_export_alone_with_their_class_key(self):
        sources = export_sources(self.config, ('a',), 1234)
        self.assertEqual(sources[0].id, 'belts')
        self.assertEqual(sources[0].label, 'Bioclimatic belts')
        self.assertFalse(sources[0].disabled)
        resolved = sources[0].resolve()
        graph = resolved.ee_object.serialize()
        for expected in ('bioclimatic_belt', 'mgci_bioclimatic_belt_classes', '1=Nival'):
            self.assertIn(expected, graph)
        self.assertEqual(resolved.default_name, 'bioclimaticbelts')
        self.assertEqual(resolved.gee_folder, f'sepal_sdg15_4_2/{self.config.aoi_label}_1234')
        self.assertEqual(resolved.vis_params['values'], [1, 2, 3, 4])
        # Without an area of interest there are no belts to export.
        self.assertNotIn('belts', [source.id for source in export_sources(replace(self.config, aoi_graph=''), ('a',), 1)])

    def test_unready_indicator_is_listed_disabled_and_switched_off_one_hidden(self):
        sources = export_sources(replace(self.config, aoi_identity=''), ('a',), 1)
        self.assertTrue(sources and all(source.disabled for source in sources))
        self.assertTrue(all(source.id.startswith('a|') for source in sources))

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


class LayerChoiceTests(ApiTestCase):
    setUp = fixtures.ScienceAdapterTests.setUp

    def test_empty_year_rows_have_no_layers(self):
        from mgci.domain.configuration import ImageSelection
        from mgci.infrastructure.layers import layer_choices
        empty = tuple(ImageSelection('', 0) for _ in range(3))
        config = replace(self.config, b=replace(self.config.b, images=empty))
        titles = [title for indicator, _, title in layer_choices(config) if indicator == 'b']
        self.assertEqual(titles, [])
        report_only = replace(self.config, b=replace(self.config.b, images=(*empty[:2], self.config.b.images[2])))
        self.assertEqual([title for indicator, _, title in layer_choices(report_only) if indicator == 'b'],
                         [f'Land cover {self.config.b.images[2].year}'])
        self.assertFalse(any(' 0' in title for _, _, title in layer_choices(self.config)))
