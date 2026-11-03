import asyncio
from dataclasses import replace
import unittest

import ee
from ee.apitestcase import ApiTestCase

from mgci.infrastructure.defaults import initial_configuration
from mgci.infrastructure.datasets import discover
from mgci.infrastructure.science import capture_aoi


class DefaultTests(unittest.TestCase):
    def test_defaults_are_packaged_and_do_not_claim_discovery(self):
        config = initial_configuration(2028)
        self.assertEqual(config.reporting_intervals[-1], 2027)
        self.assertEqual(len(config.transition.rows), 100)
        self.assertFalse(config.transition.explicitly_selected)
        self.assertIsNone(config.a.evidence)
        self.assertEqual(dict(config.a.mapping)[190], 1)
        self.assertEqual(dict(config.a.mapping)[50], 4)


class DatasetAdapterTests(ApiTestCase):
    def interface(self, histograms):
        class Interface:
            def __init__(self):
                self.calls = []
            async def get_asset_async(self, asset):
                return {'type': 'IMAGE_COLLECTION'}
            async def get_info_async(self, graph):
                self.calls.append(graph.serialize())
                if len(self.calls) == 1:
                    return [{'id': '2000', 'time': 946684800000},
                            {'id': 'lc/2015', 'time': 1420070400000},
                            {'id': 'lc/2018', 'time': 1514764800000},
                            {'id': 'lc/2021', 'time': 1609459200000}]
                return histograms.pop(0)
        return Interface()

    def config(self, **values):
        identity, graph = capture_aoi(ee.FeatureCollection([ee.Feature(ee.Geometry.Point([0, 0]))]))
        return replace(initial_configuration(2026), aoi_identity=identity, aoi_graph=graph, **values)

    def test_default_dataset_takes_classes_from_packaged_mapping_without_histograms(self):
        config = self.config()
        interface = self.interface([])
        result = asyncio.run(discover(config, 'a', interface))
        self.assertEqual(len(interface.calls), 1)
        self.assertEqual(result.evidence.classes, tuple(sorted(source for source, _ in config.a.mapping)))
        self.assertEqual(result.images[0].asset, f'{config.a.asset}/2000')
        self.assertEqual(len(result.evidence.images), 4)

    def test_custom_dataset_reads_every_image_and_normalizes_codes(self):
        from mgci.domain.configuration import Workflow
        config = self.config(workflow=Workflow.CUSTOM_RECLASSIFY)
        interface = self.interface([['10', '190'], ['10'], ['10'], ['20']])
        result = asyncio.run(discover(config, 'a', interface))
        self.assertEqual(result.evidence.classes, (10, 20, 190))
        self.assertEqual(result.images[-1].year, 2021)
        self.assertEqual(len(interface.calls), 5)
        self.assertIn('Image.select', interface.calls[-1])
        self.assertIn('Image.clipToCollection', interface.calls[-1])
        self.assertIn('Collection.map', interface.calls[-1])

    def test_bad_aoi_graph_is_rejected_before_network_call(self):
        config = replace(initial_configuration(2026), aoi_identity='bad', aoi_graph='{}')
        with self.assertRaises(ValueError):
            asyncio.run(discover(config, 'a', object()))
