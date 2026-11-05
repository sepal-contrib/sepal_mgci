import json
import unittest
from dataclasses import replace
from unittest.mock import patch

import ee
from ee.apitestcase import ApiTestCase
import pandas as pd

from mgci.domain.configuration import (
    Configuration, DatasetEvidence, ImageSelection, IndicatorConfig,
    ScalePolicy, TransitionTable, Workflow,
)
from mgci.application.state import SessionState
from mgci.infrastructure.science import build_statistics, capture_aoi, build_layer


class ScienceAdapterTests(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.network = patch('socket.socket.connect', side_effect=AssertionError('Network forbidden'))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.aoi = ee.FeatureCollection([ee.Feature(ee.Geometry.Rectangle([0, 0, 1, 1]))])
        identity, graph = capture_aoi(self.aoi)
        images = (ImageSelection('lc/2000', 2000), ImageSelection('lc/2015', 2015),
                  ImageSelection('lc/2018', 2018))
        evidence = DatasetEvidence('lc', tuple(x.asset for x in images), (10, 20), identity, 'ready')
        indicator = IndicatorConfig('lc', evidence, ((10, 1), (20, 2)), (1, 2), images)
        self.config = Configuration(identity, Workflow.CUSTOM_RECLASSIFY, indicator, indicator,
            transition=TransitionTable(((1, 1, 2), (1, 2, 1), (2, 1, 3), (2, 2, 2)), 'matrix.csv', 'digest', True),
            aoi_graph=graph)

    def test_a_adapter_preserves_existing_reduction_graph(self):
        from component.scripts.gee import reduce_regions
        request = SessionState(self.config).prepare('a', 'statistics')
        graphs = build_statistics(request)
        self.assertEqual(tuple(graphs), ('2000', '2015', '2018'))
        expected = reduce_regions(self.aoi, {10: 1, 20: 2}, False, self.config.dem,
                                  [{'asset': 'lc/2000', 'year': 2000}], None)
        self.assertEqual(graphs['2000'].serialize(), expected.serialize())

    def test_b_uses_snapshot_rows_and_never_opens_transition_path(self):
        request = SessionState(self.config).prepare('b', 'statistics')
        with patch('component.scripts.file_handler.get_current_sepal_client',
                   side_effect=AssertionError('Must not read selected file again')):
            graphs = build_statistics(request)
        self.assertEqual(tuple(graphs), ('2000_2015_2018',))
        serialized = graphs['2000_2015_2018'].serialize()
        self.assertIn('lc/2018', serialized)
        self.assertIn('Image.remap', serialized)

    def test_selected_scale_changes_graph_without_reading_live_state(self):
        state = SessionState(replace(self.config, scale=ScalePolicy('custom', 300)))
        request = state.prepare('a', 'statistics')
        state.edit(replace(self.config, scale=ScalePolicy('custom', 1000)))
        serialized = build_statistics(request)['2000'].serialize()
        def reductions(value):
            if isinstance(value, dict):
                if value.get('functionName') == 'Image.reduceRegion':
                    yield value['arguments']['scale']['constantValue']
                for child in value.values():
                    yield from reductions(child)
            elif isinstance(value, list):
                for child in value:
                    yield from reductions(child)
        self.assertEqual(list(reductions(json.loads(serialized))), [300])

    def test_canonical_layer_uses_only_classification_band(self):
        selected = replace(self.config.a, mapping=(),
                           evidence=replace(self.config.a.evidence, classes=(1, 2)))
        config = replace(self.config, workflow=Workflow.CUSTOM_CANONICAL, a=selected)
        request = SessionState(config).prepare('a', 'layer', 'lc/2000')
        expected = ee.Image('lc/2000').select(0).updateMask(ee.Image(config.biobelt).mask()).clip(self.aoi)
        self.assertEqual(build_layer(request).serialize(), expected.serialize())

    def test_unsupported_report_units_block_preparation(self):
        state = SessionState(replace(self.config, units='ha'))
        with self.assertRaises(ValueError):
            state.prepare('a', 'statistics')

    def test_tampered_aoi_identity_is_rejected(self):
        request = SessionState(replace(self.config, aoi_graph='{}')).prepare('a', 'statistics')
        with self.assertRaises(ValueError):
            build_statistics(request)

    def test_layer_uses_exact_captured_image_and_mapping(self):
        request = SessionState(self.config).prepare('a', 'layer', 'lc/2000')
        graph = build_layer(request)
        self.assertIn('lc/2000', graph.serialize())
        self.assertNotIn('lc/2018', graph.serialize())
        bad = SessionState(self.config).prepare('a', 'layer', 'unknown')
        with self.assertRaises(ValueError):
            build_layer(bad)


class NumericalFixtureTests(unittest.TestCase):
    def test_green_area_fraction_matches_hand_calculation(self):
        from component.scripts.sub_a import get_mgci
        table = pd.DataFrame([
            {'belt_class': 1, 'lc_class': 4, 'sum': 3.0},
            {'belt_class': 1, 'lc_class': 1, 'sum': 1.0},
        ])
        result = get_mgci(table)
        total = result[(result.belt_class == 'Total') & (result.lc_class == 'MGCI')]
        self.assertEqual(total.mgci.tolist(), [75.0])

    def test_b_net_area_matches_hand_calculation_from_snapshot(self):
        from component.scripts.sub_b import get_pdma_area
        transition = TransitionTable(((1, 1, 2), (1, 2, 1), (2, 1, 3), (2, 2, 2)), 'ignored.csv', 'digest', True)
        table = pd.DataFrame([
            {'belt_class': 1, 'from_lc': 1, 'to_lc': 2, 'sum': 3.0, 'category': 'baseline_transition'},
            {'belt_class': 1, 'from_lc': 2, 'to_lc': 1, 'sum': 1.0, 'category': 'baseline_transition'},
            {'belt_class': 1, 'from_lc': 1, 'to_lc': 1, 'sum': 4.0, 'category': 'baseline_transition'},
        ])
        result = get_pdma_area(table, transition)
        total = result[result.belt_class == 'Total'].iloc[0]
        self.assertEqual((total.degraded, total.improved, total.stable, total.net_degraded), (3, 1, 4, 2))
