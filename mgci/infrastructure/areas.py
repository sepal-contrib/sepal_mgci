"""AOI metadata and context layers captured from the selected geometry."""

import csv
import json

from .defaults import PARAMETERS


def area_metadata(result):
    if result is None:
        return '', ''
    if not result.method.startswith('ADMIN'):
        return result.name, ''
    iso, *names = result.name.split('_')
    with (PARAMETERS / 'm49_countries.csv').open(newline='') as stream:
        country = next((row for row in csv.DictReader(stream, delimiter=';') if row['iso31661'] == iso), None)
    if country is None:
        raise ValueError('The selected administrative area is not in the reporting country list')
    return '_'.join((country['country'], *names)), country['m49']


async def prepare_biobelt(config, gee_interface):
    import ee
    from dataclasses import asdict
    from component.scripts.biobelt import get_belt_area
    from component.parameter.visualization import biobelt_legend_data
    from component.parameter.module_parameter import BIOBELT_VIS

    aoi = ee.FeatureCollection(ee.deserializer.decode(json.loads(config.aoi_graph)))
    image = ee.Image(config.biobelt).clip(aoi)
    map_id = await gee_interface.get_map_id_async(image, BIOBELT_VIS)
    _, frame = await get_belt_area(aoi, ee.Image(config.biobelt), gee_interface=gee_interface)
    return {'graph': image.serialize(), 'url': map_id['tile_fetcher'].url_format,
            'legend': asdict(biobelt_legend_data(frame))}
