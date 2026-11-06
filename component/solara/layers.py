"""The layers table, and the map layers and floating legend it drives.

One table row per layer from ``layer_choices``: an eye shows or hides the layer, and an
export icon opens pysepal's export dialog on that layer. Export does not need the layer
on the map; it builds the image from the current settings.

Which layers are drawn is ``shown``, a set of (indicator, selector) keys that ``MgciApp``
owns and shares with ``MapOutputs``. The map's own layer list changes without telling
Solara, so a row read from it would not re-render. A layer is drawn only while its key is
shown and its artifact is current, so an edit that invalidates it removes it from the map
and turns its eye off.
"""

import json
from dataclasses import dataclass

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.export_dialog import ExportDialog
from pysepal.solara.components.export_hook import use_export_dialog
from pysepal.solara.components.legend import LegendComponent
from reacton.ipyvue import use_event

from mgci.domain.validation import readiness
from mgci.infrastructure.layers import BELTS_SOURCE, export_sources, layer_choices, prepare_layer
from mgci.infrastructure.reports import plain_data
from .actions import use_request
from .setup import readiness_text
from component.message import msg


def current_layers(state, shown=None):
    """Current layer artifacts; only those whose (indicator, selector) is in ``shown`` when given."""
    return tuple(artifact for artifact in state.history if artifact.request.slot[1] == 'layer'
                 and state.current(*artifact.request.slot) is artifact
                 and (shown is None or (artifact.request.slot[0], artifact.request.slot[2]) in shown))


def use_map_layers(state, install, remove, shown=None):
    installed = solara.use_ref(set())
    artifacts = current_layers(state, shown)
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


@dataclass(frozen=True)
class _ExportRequest:
    """One press of a row's export icon.

    The nonce makes a second press on the same row a new value, so the dialog opens again.
    """

    nonce: int
    source_id: str


@solara.component
def _ExportDialogHost(sources, request, gee_interface, drive_interface, sepal_client):
    controller = use_export_dialog(sources, gee_interface=gee_interface, drive_interface=drive_interface,
                                   sepal_client=sepal_client)

    def open_requested():
        if request.source_id:
            # Opening resets the form, the selected source included, so select after it.
            controller.open_dialog()
            controller.selected_source_id.value = request.source_id

    solara.use_effect(open_requested, [request])
    ExportDialog(controller=controller, title=msg('layers.export_title'))


@solara.component
def _IconAction(icon, tooltip, on_click, disabled=False, color=None, busy=False):
    # An icon button has no text, so the tooltip is both its hover title and its aria-label.
    button = rv.Btn(icon=True, small=True, disabled=disabled, color=color,
                    attributes={'title': tooltip, 'aria-label': tooltip},
                    children=[rv.ProgressCircular(size=16, width=2, indeterminate=True, color=color or 'primary')
                              if busy else rv.Icon(small=True, children=[icon])])

    def click(*_):
        if not disabled:
            on_click()

    use_event(button, 'click', click)


@solara.component
def _LayerRow(state, publish, indicator, selector, title, shown, gee_interface, prepare, on_export):
    key = (indicator, selector)
    request = use_request(state, publish, indicator, 'layer', lambda request: prepare_layer(request, gee_interface),
                          selection=selector, prepare=prepare, on_accept=lambda _: shown.set(shown.value | {key}))
    config = state.configuration
    prepared = state.current(indicator, 'layer', selector) is not None
    is_shown = prepared and key in shown.value
    ready = readiness(config, indicator, 'layer').ready

    def toggle():
        if request.pending:
            request.cancel()
        elif is_shown:
            shown.set(shown.value - {key})
        elif prepared:
            # Its tiles are still current: show it again without asking Earth Engine.
            shown.set(shown.value | {key})
        else:
            request.start()

    # A disabled button takes no hover, so the cell's title explains why it is disabled.
    reason = '' if ready else readiness_text(config, indicator, 'layer')
    with rv.Html(tag='tr'):
        rv.Html(tag='td', children=[title])
        rv.Html(tag='td', style_='text-align:center;', children=[indicator.upper()])
        with rv.Html(tag='td', style_='text-align:center; white-space:nowrap;',
                     attributes={'title': reason} if reason else {}):
            if request.pending:
                _IconAction('mdi-close', msg('layers.cancel', name=title), toggle, color='error', busy=True)
            else:
                _IconAction('mdi-eye' if is_shown else 'mdi-eye-off-outline',
                            msg('layers.hide' if is_shown else 'layers.show', name=title), toggle,
                            disabled=not (is_shown or ready), color='primary' if is_shown else None)
            # A cloud, not a download arrow: every export destination is remote.
            _IconAction('mdi-cloud-upload-outline', msg('layers.export', name=title), on_export,
                        disabled=not readiness(config, indicator, 'image_export').ready)


@solara.component
def _BeltRow(shown, status, on_export):
    """The bioclimatic belts: both sub-indicators use them, and they need only the AOI."""
    title = msg('layers.biobelts')
    is_shown = shown.value and status == 'ready'
    with rv.Html(tag='tr'):
        rv.Html(tag='td', children=[title])
        rv.Html(tag='td', style_='text-align:center;', children=['A, B'])
        with rv.Html(tag='td', style_='text-align:center; white-space:nowrap;'):
            _IconAction('mdi-eye' if is_shown else 'mdi-eye-off-outline',
                        msg('layers.hide' if is_shown else 'layers.show', name=title),
                        lambda: shown.set(not shown.value), disabled=status not in ('ready', 'loading'),
                        color='primary' if is_shown else None, busy=status == 'loading')
            _IconAction('mdi-cloud-upload-outline', msg('layers.export', name=title), on_export)


@solara.component
def LayerPanel(state, publish, shown, gee_interface, drive_interface, sepal_client, prepare=None, enabled=None,
               belts_shown=None, belts_status=None):
    """One row per layer of the sub-indicators switched on in the settings.

    With ``belts_shown``, the bioclimatic belts come first as soon as the AOI is set.
    """
    export_request, set_export_request = solara.use_state(_ExportRequest(0, ''))
    config = state.configuration
    indicators = ('a', 'b') if enabled is None else enabled.value
    choices = tuple(choice for choice in layer_choices(config) if choice[0] in indicators)
    belts = belts_shown is not None and bool(config.aoi_graph and config.aoi_identity)

    def exporter(source_id):
        return lambda: set_export_request(lambda previous: _ExportRequest(previous.nonce + 1, source_id))

    if not (choices or belts):
        rv.Html(tag='div', class_='pa-2 text-caption', children=[msg('layers.empty')])
    else:
        with rv.SimpleTable(dense=True):
            with rv.Html(tag='thead'), rv.Html(tag='tr'):
                rv.Html(tag='th', children=[msg('layers.columns.name')])
                rv.Html(tag='th', style_='text-align:center; white-space:nowrap;',
                        children=[msg('layers.columns.indicator')])
                rv.Html(tag='th', style_='text-align:center;', children=[msg('layers.columns.action')])
            with rv.Html(tag='tbody'):
                if belts:
                    _BeltRow(belts_shown, belts_status, exporter(BELTS_SOURCE)).key('layer-belts')
                for indicator, selector, title in choices:
                    # Keyed, so a running add stays with its layer when the rows change.
                    _LayerRow(state, publish, indicator, selector, title, shown, gee_interface, prepare,
                              exporter(f'{indicator}|{selector}')).key(f'layer-{indicator}:{selector}')
    _ExportDialogHost(export_sources(config, indicators, state.session_id), export_request,
                      gee_interface, drive_interface, sepal_client)


@solara.component
def MapOutputs(state, map_, context_legend=None, shown=None):
    """Own map layers and the floating legend at app level.

    The Results panel mounts lazily, so neither may depend on it being open. Without
    ``shown``, every current layer is drawn.
    """
    legend = solara.use_reactive('')
    collapsed = solara.use_reactive(False)
    artifacts = use_map_layers(state, lambda artifact: install_layer(map_, artifact),
                               lambda key: map_.remove_layer(key, none_ok=True),
                               None if shown is None else shown.value)
    entries = ([('biobelts', msg('layers.biobelts'), context_legend)] if context_legend else []) + [
        (artifact.request.request_id, artifact.payload['title'], {'items': plain_data(artifact.payload['legend'])}) for artifact in artifacts]
    effective = next((entry for entry in entries if entry[0] == legend.value), entries[-1] if entries else None)
    LegendComponent(legend_data=effective[2] if effective else {}, visible=bool(effective),
                    collapsed=collapsed.value, event_set_collapsed=collapsed.set,
                    selector_options=[{'value': key, 'text': title} for key, title, _ in entries],
                    selected=effective[0] if effective else None, event_set_selected=legend.set)
