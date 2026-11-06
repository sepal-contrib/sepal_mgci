"""AOI context layers share the same stale-response rules as thematic outputs."""

import logging
import json

import solara
from pysepal.solara.notifications import use_notifications

from component.message import msg
from mgci.infrastructure.areas import prepare_biobelt

log = logging.getLogger('MGCI.solara.areas')


def install_biobelt(map_, payload):
    import ee
    from pysepal.mapping.layer import EELayer

    map_.add_layer(EELayer(ee_object=ee.Image(ee.deserializer.decode(json.loads(payload['graph']))),
                          url=payload['url'], name=msg('layers.biobelts'), attribution='Google Earth Engine',
                          max_zoom=24), key='biobelts')


@solara.component
def BiobeltOverlay(config, map_, gee_interface, on_legend, shown, on_status=None):
    """Draw the belts of the area of interest while ``shown`` is true.

    Hiding keeps the prepared tiles, so showing again needs no Earth Engine call. A new
    area of interest shows its belts again, because they are the check of that area.
    """
    notifications = use_notifications()
    identity = (config.aoi_identity, config.biobelt)

    @solara.lab.use_task(dependencies=[identity], raise_error=False, prefer_threaded=False)
    async def task():
        if not config.aoi_graph:
            return None
        try:
            return identity, await prepare_biobelt(config, gee_interface), None
        except Exception as error:
            log.exception('Bioclimatic belt overlay failed')
            return identity, None, str(error)

    def clear():
        map_.remove_layer('biobelts', none_ok=True)
        on_legend(None)
        shown.set(True)
    solara.use_effect(clear, [identity])

    result = task.value if task.finished and task.value is not None and task.value[0] == identity else None
    status = ('loading' if task.pending else None if result is None
              else 'error' if result[2] else 'ready') if config.aoi_graph else None
    solara.use_effect(lambda: on_status and on_status(status), [status])

    def report():
        if result is not None and result[2]:
            notifications.error(result[2])
    solara.use_effect(report, [result])

    def receive():
        if result is None or result[2]:
            return
        payload = result[1]
        if shown.value:
            install_biobelt(map_, payload)
            on_legend(payload['legend'])
        else:
            map_.remove_layer('biobelts', none_ok=True)
            on_legend(None)
    solara.use_effect(receive, [result, shown.value])
    solara.use_effect(lambda: lambda: map_.remove_layer('biobelts', none_ok=True), [])
