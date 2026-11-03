"""Map layers for accepted requests, and export sources built from the current settings."""

import logging
import json
from types import SimpleNamespace

from .defaults import classification_labels
from .science import build_layer

log = logging.getLogger('MGCI.infrastructure.layers')


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


def _image_parts(request):
    """Graphs and keys shared by the map layer and the export; no Earth Engine calls."""
    import ee
    from component.parameter.module_parameter import BIOBELT_LEGEND

    image = build_layer(request)
    aoi = ee.FeatureCollection(ee.deserializer.decode(json.loads(request.configuration.aoi_graph)))
    land_cover = request.slot[0] == 'a' or request.slot[2].endswith('|land_cover')
    labels = classification_labels(getattr(request.configuration, request.slot[0])) if land_cover else (
        (1, 'Degraded', '#8B0000'), (2, 'Stable', '#B0C4DE'), (3, 'Improved', '#008000'))
    vis = {'min': labels[0][0], 'max': labels[-1][0], 'palette': [row[2] for row in labels],
           'values': [row[0] for row in labels], 'labels': [row[1] for row in labels]}
    class_key = '; '.join(f'{code}={name}' for code, name, _ in labels)
    if not land_cover:
        class_key = f'0=Unclassified; {class_key}'
    belt_key = '; '.join(f'{code}={name}' for code, (name, _) in BIOBELT_LEGEND.items() if isinstance(code, int))
    belt = ee.Image(request.configuration.biobelt).rename('bioclimatic_belt').clip(aoi).updateMask(image.mask()).toInt16()
    export_image = image.toInt16().addBands(belt).set({
        'mgci_pixel_classes': class_key, 'mgci_bioclimatic_belt_classes': belt_key,
    })
    title = next((title for indicator, selector, title in layer_choices(request.configuration)
                  if (indicator, selector) == (request.slot[0], request.slot[2])), request.slot[2])
    return SimpleNamespace(image=image, aoi=aoi, labels=labels, vis=vis, class_key=class_key,
                           belt_key=belt_key, export_image=export_image, title=title)


async def prepare_layer(request, gee_interface) -> dict:
    import ee

    log.debug('Preparing layer %s', '/'.join(filter(None, request.slot)))
    parts = _image_parts(request)
    image, labels = parts.image, parts.labels
    metadata = await gee_interface.get_info_async(ee.Dictionary({
        'scale': image.projection().nominalScale(), 'bands': image.bandNames(),
        'bounds': parts.aoi.bounds().coordinates().get(0),
    }))
    codes = [row[0] for row in labels]
    categorical = image.remap(codes, list(range(len(codes))))
    map_id = await gee_interface.get_map_id_async(categorical, {'palette': parts.vis['palette'], 'min': 0,
                                                                'max': len(codes) - 1})
    return {'graph': image.serialize(), 'vis': parts.vis, 'title': parts.title,
            'legend': [{'label': name, 'color': color} for _, name, color in labels],
            'class_key': parts.class_key, 'belt_key': parts.belt_key,
            'scale': request.configuration.scale.metres or metadata['scale'], 'bands': metadata['bands'],
            'url': map_id['tile_fetcher'].url_format, 'bounds': metadata['bounds']}


def export_sources(config, indicators, session_id):
    """One pysepal export source per layer, built from ``config`` when the user exports.

    Layers whose indicator is not ready are listed disabled, as the dialog shows them.
    """
    from pysepal.solara.components.export import ExportSource, ResolvedExport
    from component.message import cm
    from component.scripts.aoi_geometry import aoi_bbox
    from mgci.application.state import Request
    from mgci.domain.provenance import scientific_identity
    from mgci.domain.validation import readiness

    headers = {'a': cm.layers.sub_a_header, 'b': cm.layers.sub_b_header}
    ready = {key: readiness(config, key, 'image_export').ready for key in ('a', 'b')}
    sources = []
    for indicator, selector, title in layer_choices(config):
        if indicator not in indicators:
            continue
        slot = (indicator, 'image_export', selector)

        def resolve(slot=slot, title=title):
            request = Request('', f'export:{slot[0]}:{slot[2]}', slot, 0,
                              scientific_identity(config, slot[0], 'image_export'), config)
            parts = _image_parts(request)
            log.debug('Resolved export %s', '/'.join(filter(None, slot)))
            return ResolvedExport(
                ee_object=parts.export_image,
                # Legacy destinations: <asset root>/sepal_sdg15_4_2/<AOI>_<session>/SubA_landcover2000.
                default_name=f"{'SubA' if slot[0] == 'a' else 'SubB'}_{title.replace(' ', '').lower()}",
                gee_folder=f'sepal_sdg15_4_2/{config.aoi_label}_{session_id}',
                # Per-feature bounds, as legacy: dissolving dense country boundaries hits EE edge limits.
                region=aoi_bbox(parts.aoi),
                # The processing scale when set, else the legacy export default of 1000 m.
                default_scale=config.scale.metres or 1000,
                max_pixels=int(1e13), vis_params=parts.vis,
            )

        # The dialog lists A and B together, so the label names the sub-indicator.
        sources.append(ExportSource(id=f'{indicator}|{selector}', label=f'{title} ({headers[indicator]})',
                                    kind='image', resolve=resolve,
                                    description=headers[indicator], disabled=not ready[indicator]))
    return tuple(sources)
