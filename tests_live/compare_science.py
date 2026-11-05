"""Read-only live check that the app statistics match a direct `reduce_regions` call; prints one JSON row per case, never exports.

Needs Earth Engine credentials.
"""

import asyncio
from dataclasses import replace
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ee
from pysepal.scripts.utils import init_ee
from pysepal.scripts.gee_interface import GEEInterface

from mgci.application.state import SessionState
from mgci.domain.configuration import DatasetEvidence, ScalePolicy
from mgci.infrastructure.defaults import initial_configuration, PARAMETERS
from mgci.infrastructure.science import capture_aoi, build_statistics
from mgci.infrastructure.layers import prepare_layer


def compare(left, right):
    if isinstance(left, dict):
        assert set(left) == set(right), (set(left), set(right))
        for key in left:
            compare(left[key], right[key])
    elif isinstance(left, list):
        assert len(left) == len(right)
        for a, b in zip(left, right):
            compare(a, b)
    elif isinstance(left, (int, float)):
        assert math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-8), (left, right)
    else:
        assert left == right, (left, right)


async def main():
    init_ee()
    from component.scripts.gee import reduce_regions
    interface = GEEInterface()
    evidence = []
    try:
        for name, bounds, scale, rsa in (
            ('Alps', [8.0, 46.4, 8.1, 46.5], None, False),
            ('Andes', [-74.1, 4.5, -74.0, 4.6], 100, False),
            ('Himalaya', [85.2, 27.7, 85.3, 27.8], 300, True),
            ('Australian Alps', [148.2, -36.5, 148.3, -36.4], 1000, False),
        ):
            aoi = ee.FeatureCollection([ee.Feature(ee.Geometry.Rectangle(bounds))])
            identity, graph = capture_aoi(aoi)
            config = initial_configuration(2026)
            selected = replace(config.a, evidence=DatasetEvidence(config.a.asset,
                tuple(image.asset for image in config.a.images), tuple(code for code, _ in config.a.mapping), identity, 'ready'))
            config = replace(config, aoi_identity=identity, aoi_graph=graph, aoi_name=name,
                             a=selected, b=selected, rsa=rsa, scale=ScalePolicy() if scale is None else ScalePolicy('custom', scale))
            state = SessionState(config)
            for indicator in ('a', 'b'):
                request = state.prepare(indicator, 'statistics')
                migrated = build_statistics(request)
                images = getattr(config, indicator).images
                groups = [(image,) for image in images] if indicator == 'a' else [images]
                original = {'_'.join(str(image.year) for image in group): reduce_regions(
                    aoi, dict(selected.mapping), rsa, config.dem,
                    [{'asset': image.asset, 'year': image.year} for image in group],
                    str(PARAMETERS / 'transition_matrix.csv'), scale) for group in groups}
                result = await interface.get_info_async(ee.Dictionary({'migration': ee.Dictionary(migrated), 'reference': ee.Dictionary(original)}))
                compare(result['migration'], result['reference'])
                state.accept(request, result['migration'])
                row = {'region': name, 'indicator': indicator, 'scale': scale or 'native', 'rsa': rsa,
                       'relative_tolerance': 1e-9, 'absolute_tolerance_sqkm': 1e-8, 'status': 'passed'}
                evidence.append(row)
                print(json.dumps(row), flush=True)
            layer = await prepare_layer(state.prepare('a', 'layer', selected.images[0].asset), interface)
            assert layer['url'] and layer['bands'] and layer['scale'] > 0
            print(json.dumps({'region': name, 'layer': 'passed', 'resolved_scale': layer['scale']}), flush=True)
    finally:
        interface.close()


if __name__ == '__main__':
    asyncio.run(main())
