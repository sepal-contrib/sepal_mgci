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


def reporting_admin_items(level=0, parent_code=''):
    """Retain the reference app's M49-filtered country list."""
    from importlib.resources import files
    import pandas as pd
    from pysepal.solara.components.aoi import fetch_admin_items

    items = fetch_admin_items(level, parent_code)
    if level:
        return items
    with (PARAMETERS / 'm49_countries.csv').open(newline='') as stream:
        countries = {row['iso31661'] for row in csv.DictReader(stream, delimiter=';')}
    frame = pd.read_parquet(files('pygaul').joinpath('data/gaul_database.parquet'))
    allowed = set(frame.loc[frame.iso3_code.isin(countries), 'gaul0_code'].astype(str))
    return [item for item in items if item['value'] in allowed]


async def prepare_area_preview(result, gee_interface):
    """Render the AOI like the legacy ``add_ee_layer(fc, {})``: theme primary colour, one tile URL per theme."""
    import asyncio
    import ee
    from pysepal.mapping.visualization import process_vis_params
    from pysepal.frontend import styles as ss
    from component.scripts.aoi_geometry import aoi_bbox

    collection = ee.FeatureCollection(result.feature_collection)
    themes = {dark: {'color': colors['primary']} for dark, colors in ss.THEMES.items()}
    processed = {dark: process_vis_params(collection, vis, {}, False) for dark, vis in themes.items()}
    map_ids = await asyncio.gather(*(gee_interface.get_map_id_async(image, vis)
                                     for image, _, vis in processed.values()))
    coordinates = await gee_interface.get_info_async(aoi_bbox(collection).coordinates().get(0))
    urls = {dark: map_id['tile_fetcher'].url_format for dark, map_id in zip(processed, map_ids)}
    return collection, urls, (*coordinates[0], *coordinates[2])
