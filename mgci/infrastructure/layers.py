"""Prepare map data without mutating a map; export only accepted layer graphs."""

import json

from .defaults import classification_labels
from .reports import plain_data
from .science import build_layer


def layer_choices(config):
    """(indicator, selector, title) for every layer, with the legacy selector titles."""
    from component.message import cm

    names = cm.layers
    choices = [('a', image.asset, f'{names.land_cover} {image.year}') for image in config.a.images]
    for image in config.b.images[2:]:
        choices.append(('b', f'{image.asset}|final_degradation', f'{names.final_degradation} {image.year}'))
    if len(config.b.images) >= 3:
        choices.append(('b', f'{config.b.images[2].asset}|baseline_degradation', names.baseline_degradation))
    choices += [('b', f'{image.asset}|report_degradation', f'{names.report_degradation} {image.year}')
                for image in config.b.images[2:]]
    choices += [('b', f'{image.asset}|land_cover', f'{names.land_cover} {image.year}') for image in config.b.images]
    return tuple(choices)


async def _prepare_image(request, gee_interface, display) -> dict:
    import ee
    from component.parameter.module_parameter import BIOBELT_LEGEND

    image = build_layer(request)
    aoi = ee.FeatureCollection(ee.deserializer.decode(json.loads(request.configuration.aoi_graph)))
    land_cover = request.slot[0] == 'a' or request.slot[2].endswith('|land_cover')
    labels = classification_labels(getattr(request.configuration, request.slot[0])) if land_cover else (
        (1, 'Degraded', '#8B0000'), (2, 'Stable', '#B0C4DE'), (3, 'Improved', '#008000'))
    vis = {'min': labels[0][0], 'max': labels[-1][0], 'palette': [row[2] for row in labels]}
    details = {
        'scale': image.projection().nominalScale(), 'projection': image.projection(), 'bands': image.bandNames(),
    }
    if display:
        details['bounds'] = aoi.bounds().coordinates().get(0)
    metadata = await gee_interface.get_info_async(ee.Dictionary(details))
    codes = [row[0] for row in labels]
    vis['values'] = codes
    vis['labels'] = [row[1] for row in labels]
    title = next((title for indicator, selector, title in layer_choices(request.configuration)
                  if (indicator, selector) == (request.slot[0], request.slot[2])), request.slot[2])
    class_key = '; '.join(f'{code}={name}' for code, name, _ in labels)
    if not land_cover:
        class_key = f'0=Unclassified; {class_key}'
    belt_key = '; '.join(f'{code}={name}' for code, (name, _) in BIOBELT_LEGEND.items() if isinstance(code, int))
    belt = ee.Image(request.configuration.biobelt).rename('bioclimatic_belt').clip(aoi).updateMask(image.mask()).toInt16()
    export_image = image.toInt16().addBands(belt).set({
        'mgci_pixel_classes': class_key, 'mgci_bioclimatic_belt_classes': belt_key,
    })
    payload = {'graph': image.serialize(), 'export_graph': export_image.serialize(),
            'export_bands': [*metadata['bands'], 'bioclimatic_belt'], 'class_key': class_key, 'belt_key': belt_key,
            'vis': vis, 'legend': [{'label': name, 'color': color} for _, name, color in labels],
            'title': title, 'scale': request.configuration.scale.metres or metadata['scale'],
            'projection': metadata['projection'], 'bands': metadata['bands']}
    if display:
        categorical = image.remap(codes, list(range(len(codes))))
        map_id = await gee_interface.get_map_id_async(categorical, {'palette': vis['palette'], 'min': 0, 'max': len(codes) - 1})
        payload['url'] = map_id['tile_fetcher'].url_format
        payload['bounds'] = metadata['bounds']
    return payload


async def prepare_layer(request, gee_interface) -> dict:
    return await _prepare_image(request, gee_interface, display=True)


async def prepare_export(request, gee_interface) -> dict:
    return await _prepare_image(request, gee_interface, display=False)


def export_source(state, artifact):
    import ee
    from pysepal.solara.components.export import ExportSource, ResolvedExport
    from component.scripts.aoi_geometry import aoi_bbox

    def resolve():
        captured = state.export_artifact(artifact.request)
        payload = plain_data(captured.payload)
        config = captured.request.configuration
        aoi = ee.FeatureCollection(ee.deserializer.decode(json.loads(config.aoi_graph)))
        return ResolvedExport(
            ee_object=ee.Image(ee.deserializer.decode(json.loads(payload['export_graph']))),
            # Legacy destinations: <asset root>/sepal_sdg15_4_2/<AOI>_<session>/SubA_landcover2000.
            default_name=f"{'SubA' if captured.request.slot[0] == 'a' else 'SubB'}_"
                         f"{payload['title'].replace(' ', '').lower()}",
            gee_folder=f'sepal_sdg15_4_2/{config.aoi_label}_{state.session_id}',
            # The legacy slider runs 10-2000 m in 10 m steps; start it at the processing scale.
            # Per-feature bounds, as legacy: dissolving dense country boundaries hits EE edge limits.
            region=aoi_bbox(aoi), default_scale=min(2000, max(10, round(payload['scale'] / 10) * 10)),
            bands=tuple(payload['export_bands']), default_bands=tuple(payload['export_bands']),
            max_pixels=int(1e13), vis_params={**payload['vis'], 'bands': payload['bands']},
        )

    return ExportSource(id=artifact.request.request_id, label=artifact.payload['title'], kind='image', resolve=resolve)
