"""Map layers for accepted requests, and export sources built from the current settings."""

import logging
import json
from types import SimpleNamespace

from .defaults import classification_labels
from .science import build_layer

log = logging.getLogger('MGCI.infrastructure.layers')

# Classes of the degradation layers. The English names go into the exported metadata.
IMPACT_CLASSES = ((1, 'Degraded', '#8B0000'), (2, 'Stable', '#B0C4DE'), (3, 'Improved', '#008000'))


# Export source id of the bioclimatic belts, which have no sub-indicator.
BELTS_SOURCE = 'belts'

# Default export names use these English stems in every language: a translated
# title would put accents, which asset names cannot hold, into the name.
EXPORT_STEMS = {'land_cover': 'landcover', 'final_degradation': 'totaldegradation',
                'baseline_degradation': 'baselinedegradation', 'report_degradation': 'reportdegradation'}


def _layers(config):
    """(indicator, selector, kind, year) for every layer; the baseline degradation has no year."""
    def complete(images):
        # A year row without an image or a year has no layer yet.
        return tuple(image for image in images if image.asset and image.year > 0)

    layers = [('a', image.asset, 'land_cover', image.year) for image in complete(config.a.images)]
    baseline, reports = config.b.images[:2], complete(config.b.images[2:])
    if len(complete(baseline)) == 2:
        for image in reports:
            layers.append(('b', f'{image.asset}|final_degradation', 'final_degradation', image.year))
        if config.b.images[2:3] and config.b.images[2] in reports:
            layers.append(('b', f'{config.b.images[2].asset}|baseline_degradation', 'baseline_degradation', None))
        layers += [('b', f'{image.asset}|report_degradation', 'report_degradation', image.year) for image in reports]
    layers += [('b', f'{image.asset}|land_cover', 'land_cover', image.year) for image in complete(config.b.images)]
    return tuple(layers)


def layer_choices(config):
    """(indicator, selector, title) for every layer that the configuration can show."""
    from component.message import msg

    return tuple((indicator, selector, msg(f'layers.{kind}') if year is None else f'{msg(f"layers.{kind}")} {year}')
                 for indicator, selector, kind, year in _layers(config))


def _image_parts(request):
    """Graphs and keys shared by the map layer and the export; no Earth Engine calls."""
    import ee
    from component.message import msg
    from component.parameter.module_parameter import BIOBELT_LEGEND

    image = build_layer(request)
    aoi = ee.FeatureCollection(ee.deserializer.decode(json.loads(request.configuration.aoi_graph)))
    land_cover = request.slot[0] == 'a' or request.slot[2].endswith('|land_cover')
    labels = classification_labels(getattr(request.configuration, request.slot[0])) if land_cover else IMPACT_CLASSES
    shown = labels if land_cover else tuple((code, msg(f'layers.legend.{code}'), color) for code, _, color in labels)
    vis = {'min': shown[0][0], 'max': shown[-1][0], 'palette': [row[2] for row in shown],
           'values': [row[0] for row in shown], 'labels': [row[1] for row in shown]}
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
    return SimpleNamespace(image=image, aoi=aoi, labels=shown, vis=vis, class_key=class_key,
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
    from component.message import msg
    from component.scripts.aoi_geometry import aoi_bbox
    from mgci.application.state import Request
    from mgci.domain.provenance import scientific_identity
    from mgci.domain.validation import readiness

    headers = {'a': msg('layers.sub_a_header'), 'b': msg('layers.sub_b_header')}
    ready = {key: readiness(config, key, 'image_export').ready for key in ('a', 'b')}
    sources = []
    if config.aoi_graph and config.aoi_identity:
        sources.append(ExportSource(id=BELTS_SOURCE, label=msg('layers.biobelts'), kind='image',
                                    resolve=lambda: _belt_export(config, session_id)))
    for (indicator, selector, title), (*_, kind, year) in zip(layer_choices(config), _layers(config)):
        if indicator not in indicators:
            continue
        slot = (indicator, 'image_export', selector)

        def resolve(slot=slot, stem=f'{EXPORT_STEMS[kind]}{year or ""}'):
            request = Request('', f'export:{slot[0]}:{slot[2]}', slot, 0,
                              scientific_identity(config, slot[0], 'image_export'), config)
            parts = _image_parts(request)
            log.debug('Resolved export %s', '/'.join(filter(None, slot)))
            return ResolvedExport(
                ee_object=parts.export_image,
                # Destinations: <asset root>/sepal_sdg15_4_2/<AOI>_<session>/SubA_landcover2000.
                default_name=f"{'SubA' if slot[0] == 'a' else 'SubB'}_{stem}",
                gee_folder=f'sepal_sdg15_4_2/{config.aoi_label}_{session_id}',
                # Per-feature bounds: dissolving dense country boundaries hits EE edge limits.
                region=aoi_bbox(parts.aoi),
                # The processing scale when set, else 1000 m.
                default_scale=config.scale.metres or 1000,
                max_pixels=int(1e13), vis_params=parts.vis,
            )

        # The dialog lists A and B together, so the label names the sub-indicator.
        sources.append(ExportSource(id=f'{indicator}|{selector}', label=f'{title} ({headers[indicator]})',
                                    kind='image', resolve=resolve,
                                    description=headers[indicator], disabled=not ready[indicator]))
    return tuple(sources)


def _belt_export(config, session_id):
    """The belts of the AOI alone, with their class key, as the other exports carry it."""
    import ee
    from pysepal.solara.components.export import ResolvedExport
    from component.parameter.module_parameter import BIOBELT_LEGEND, belt_name
    from component.scripts.aoi_geometry import aoi_bbox

    aoi = ee.FeatureCollection(ee.deserializer.decode(json.loads(config.aoi_graph)))
    codes = [code for code in BIOBELT_LEGEND if isinstance(code, int)]
    belt_key = '; '.join(f'{code}={BIOBELT_LEGEND[code][0]}' for code in codes)
    image = (ee.Image(config.biobelt).rename('bioclimatic_belt').clip(aoi).toInt16()
             .set({'mgci_bioclimatic_belt_classes': belt_key}))
    return ResolvedExport(
        ee_object=image, default_name='bioclimaticbelts',
        gee_folder=f'sepal_sdg15_4_2/{config.aoi_label}_{session_id}', region=aoi_bbox(aoi),
        default_scale=config.scale.metres or 1000, max_pixels=int(1e13),
        vis_params={'min': codes[0], 'max': codes[-1], 'palette': [BIOBELT_LEGEND[code][1] for code in codes],
                    'values': codes, 'labels': [belt_name(code) for code in codes]})
