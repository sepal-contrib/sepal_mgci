"""Capture the full image/class scope on explicit dataset inspection."""

from datetime import datetime, timezone
from hashlib import sha256
import json
import re

from mgci.domain.codes import class_code
from mgci.domain.configuration import DatasetDiscovery, DatasetEvidence, ImageSelection


def _year(metadata):
    timestamp = metadata.get('time')
    if timestamp is not None:
        return datetime.fromtimestamp(timestamp / 1000, timezone.utc).year
    found = re.search(r'(?:^|[/_])((?:19|20)\d{2})(?:$|[_-])', metadata['id'])
    return int(found.group(1)) if found else 0


async def discover(config, indicator, gee_interface) -> DatasetDiscovery:
    import ee
    from component.scripts.aoi_geometry import aoi_bbox

    if not config.aoi_graph or sha256(config.aoi_graph.encode()).hexdigest() != config.aoi_identity:
        raise ValueError('Select an area of interest before getting classes')
    selected = getattr(config, indicator)
    aoi = ee.FeatureCollection(ee.deserializer.decode(json.loads(config.aoi_graph)))
    metadata = await gee_interface.get_asset_async(selected.asset)
    asset_type = metadata.get('type', '').upper()
    if asset_type == 'IMAGE_COLLECTION':
        collection = ee.ImageCollection(selected.asset)
        records = await gee_interface.get_info_async(collection.toList(collection.size()).map(
            lambda item: ee.Dictionary({'id': ee.Image(item).id(), 'time': ee.Image(item).get('system:time_start')})
        ))
    elif asset_type == 'IMAGE':
        records = [{'id': selected.asset, 'time': metadata.get('properties', {}).get('system:time_start')}]
    else:
        raise ValueError('Select an Earth Engine image or image collection')
    if asset_type == 'IMAGE_COLLECTION':
        records = [{**record, 'id': record['id'] if '/' in record['id']
                    else f"{selected.asset.rstrip('/')}/{record['id']}"} for record in records]
    if not records or len({record['id'] for record in records}) != len(records):
        raise ValueError('Dataset contains no images or duplicate image identifiers')
    images = tuple(sorted((ImageSelection(row['id'], _year(row)) for row in records), key=lambda image: (image.year, image.asset)))
    classes = set()
    for selection in images:
        image = ee.Image(selection.asset).select(0)
        histogram = image.clipToCollection(aoi).reduceRegion(ee.Reducer.frequencyHistogram(), geometry=aoi_bbox(aoi),
                                       scale=image.projection().nominalScale(), maxPixels=1e13)
        keys = ee.Dictionary(histogram.get(image.bandNames().get(0), ee.Dictionary({}))).keys()
        classes.update(class_code(value) for value in await gee_interface.get_info_async(keys))
    version = sha256(json.dumps(records, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    evidence = DatasetEvidence(selected.asset, tuple(image.asset for image in images),
                               tuple(sorted(classes)), config.aoi_identity, 'ready', version)
    return DatasetDiscovery(evidence, images)
