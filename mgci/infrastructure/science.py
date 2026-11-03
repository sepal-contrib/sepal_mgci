"""Adapt immutable requests to the existing Earth Engine scientific kernels."""

import logging
from hashlib import sha256
import time
import json

from mgci.application.state import Request
from mgci.domain.validation import readiness
from mgci.domain.reporting import reporting_breakpoints

log = logging.getLogger('MGCI.infrastructure.science')


def capture_aoi(feature_collection) -> tuple[str, str]:
    graph = json.dumps(json.loads(feature_collection.serialize()), sort_keys=True, separators=(',', ':'))
    return sha256(graph.encode()).hexdigest(), graph


def _inputs(request: Request):
    import ee

    config = request.configuration
    indicator, purpose, _ = request.slot
    if not readiness(config, indicator, purpose).ready:
        raise ValueError('Request configuration is not ready')
    if not config.aoi_graph or sha256(config.aoi_graph.encode()).hexdigest() != config.aoi_identity:
        raise ValueError('AOI graph does not match request provenance')
    aoi = ee.FeatureCollection(ee.deserializer.decode(json.loads(config.aoi_graph)))
    return config, getattr(config, indicator), aoi


def build_statistics(request: Request) -> dict:
    from component.scripts.gee import reduce_regions

    if request.slot[1] not in ('statistics', 'chart'):
        raise ValueError('Not a statistics request')
    config, selected, aoi = _inputs(request)
    if config.units != 'sqkm':
        raise ValueError('Scientific report reductions currently use square kilometres')
    images = selected.images
    if request.slot[0] == 'a':
        used = {image for _, sources in reporting_breakpoints(images, config.reporting_intervals) for image in sources}
        images = tuple(image for image in images if image in used)
    groups = ((image,) for image in images) if request.slot[0] == 'a' else (
        (images[0], images[1], image) for image in images[2:]
    )
    return {
        '_'.join(str(image.year) for image in group): reduce_regions(
            aoi=aoi, remap_matrix=dict(selected.mapping), rsa=config.rsa, dem=config.dem,
            lc_years=[{'asset': image.asset, 'year': image.year} for image in group],
            transition_matrix=config.transition,
            scale=config.scale.metres, biobelt_asset=config.biobelt,
        ) for group in groups
    }


async def calculate(request: Request, gee_interface) -> dict:
    graphs = build_statistics(request)
    config = request.configuration
    log.info('Calculating sub-indicator %s for %s: groups %s, scale %s, rsa %s', request.slot[0].upper(),
             config.aoi_name or config.aoi_label, ', '.join(graphs), config.scale.metres or 'native', config.rsa)
    started = time.monotonic()
    # Use the session interface on its owning loop; inputs are already captured.
    results = {key: await gee_interface.get_info_async(graph) for key, graph in graphs.items()}
    log.info('Sub-indicator %s calculated in %.1f s', request.slot[0].upper(), time.monotonic() - started)
    return results


def build_layer(request: Request):
    import ee
    from component.scripts.gee import get_transition, no_remap

    if request.slot[1] not in ('layer', 'image_export'):
        raise ValueError('Not a layer request')
    config, selected, aoi = _inputs(request)
    selection = request.slot[2]
    if request.slot[0] == 'a':
        if selection not in {image.asset for image in selected.images}:
            raise ValueError('Select an image from the validated request')
        layer = no_remap(ee.Image(selection).select(0), dict(selected.mapping))
    else:
        # A B layer selector is '<report asset>|<band>'.
        asset, separator, band = selection.rpartition('|')
        if not separator or band not in ('land_cover', 'report_degradation', 'baseline_transition', 'report_transition',
                                         'baseline_degradation', 'final_degradation'):
            raise ValueError('Invalid transition layer selection')
        allowed = selected.images if band == 'land_cover' else selected.images[2:]
        if asset not in {image.asset for image in allowed}:
            raise ValueError('Select an image from the validated request')
        if band == 'land_cover':
            # Legacy band names from get_transition: baseline start, baseline end, report.
            position = [image.asset for image in selected.images].index(asset)
            name = ('land_cover_start', 'land_cover_end')[position] if position < 2 else 'land_cover_report'
            layer = no_remap(ee.Image(asset).select(0), dict(selected.mapping)).rename(name)
            return layer.updateMask(ee.Image(config.biobelt).mask()).clip(aoi)
        layer = get_transition(
            ee.Image(selected.images[0].asset).select(0),
            ee.Image(selected.images[1].asset).select(0), ee.Image(asset).select(0),
            aoi, config.transition, dict(selected.mapping),
        ).select(band)
    return layer.updateMask(ee.Image(config.biobelt).mask()).clip(aoi)
