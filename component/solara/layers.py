"""Publish accepted layers synchronously and remove them on invalidation."""

import json

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.legend import LegendComponent

from mgci.infrastructure.layers import layer_choices, prepare_layer
from mgci.infrastructure.reports import plain_data
from .actions import RequestAction
from .setup import readiness_text
from .messages import msg
from component.message import cm


def current_layers(state):
    return tuple(artifact for artifact in state.history if artifact.request.slot[1] == 'layer'
                 and state.current(*artifact.request.slot) is artifact)


def use_map_layers(state, install, remove):
    installed = solara.use_ref(set())
    artifacts = current_layers(state)
    ids = tuple(artifact.request.request_id for artifact in artifacts)

    def synchronize():
        for obsolete in installed.current - set(ids):
            remove(obsolete)
        installed.current.intersection_update(ids)
        for artifact in artifacts:
            if artifact.request.request_id not in installed.current:
                install(artifact)
                installed.current.add(artifact.request.request_id)

    def lifetime():
        def dispose():
            for key in tuple(installed.current):
                remove(key)
            installed.current.clear()
        return dispose

    solara.use_effect(synchronize, [ids])
    solara.use_effect(lifetime, [])
    return artifacts


def install_layer(map_, artifact):
    import ee
    from pysepal.mapping.layer import EELayer

    payload = plain_data(artifact.payload)
    layer = EELayer(ee_object=ee.Image(ee.deserializer.decode(json.loads(payload['graph']))),
                    url=payload['url'], attribution='Google Earth Engine', name=payload['title'], max_zoom=24)
    map_.add_layer(layer, key=artifact.request.request_id)
    bounds = payload['bounds']
    map_.zoom_bounds((*bounds[0], *bounds[2]))


@solara.component
def LayerPanel(state, publish, map_, gee_interface, drive_interface, sepal_client, prepare=None, before_use=None,
               enabled=None):
    selected = solara.use_reactive('')
    # Like the legacy selector, offer only the indicators switched on in the settings.
    choices = tuple(choice for choice in layer_choices(state.configuration) if enabled is None or choice[0] in enabled.value)
    indexed = {f'{indicator}:{selector}': (indicator, selector, title) for indicator, selector, title in choices}
    current = indexed.get(selected.value)
    items = []
    for key, header in (('a', cm.layers.sub_a_header), ('b', cm.layers.sub_b_header)):
        group = [{'text': title.removeprefix('Land cover ') if key == 'a' else title, 'value': value}
                 for value, (indicator, _, title) in indexed.items() if indicator == key]
        if group:
            items.extend([{'header': header}, *group])
    with rv.Html(tag='div', class_='pa-2'):
        indicator, selector, _ = current or ('a', '', '')
        # A short hint, not an alert: it explains the disabled "Add layer" for this sub-indicator.
        reason = readiness_text(state.configuration, indicator, 'layer') if current is not None else ''
        with rv.Col():
            rv.Select(label=msg('layers.label'), items=items, v_model=selected.value, on_v_model=selected.set,
                      hint=reason, persistent_hint=bool(reason), style_='max-width:362px;')
        with rv.Html(tag='div', class_='d-block mt-2', style_='width:100%;'):
            RequestAction(state, publish, indicator, 'layer', lambda request: prepare_layer(request, gee_interface),
                          label=msg('layers.add'), selection=selector, prepare=prepare, disabled=current is None,
                          block=True)


@solara.component
def MapOutputs(state, map_, context_legend=None):
    """Own map layers and the floating legend at app level, like the legacy MapLegend.

    The Results panel mounts lazily, so neither may depend on it being open.
    """
    legend = solara.use_reactive('')
    collapsed = solara.use_reactive(False)
    artifacts = use_map_layers(state, lambda artifact: install_layer(map_, artifact), lambda key: map_.remove_layer(key, none_ok=True))
    entries = ([('biobelts', 'Bioclimatic belts', context_legend)] if context_legend else []) + [
        (artifact.request.request_id, artifact.payload['title'], {'items': plain_data(artifact.payload['legend'])}) for artifact in artifacts]
    effective = next((entry for entry in entries if entry[0] == legend.value), entries[-1] if entries else None)
    LegendComponent(legend_data=effective[2] if effective else {}, visible=bool(effective),
                    collapsed=collapsed.value, event_set_collapsed=collapsed.set,
                    selector_options=[{'value': key, 'text': title} for key, title, _ in entries],
                    selected=effective[0] if effective else None, event_set_selected=legend.set)
