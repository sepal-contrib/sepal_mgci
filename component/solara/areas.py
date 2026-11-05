"""AOI context layers share the same stale-response rules as thematic outputs."""

import logging
import json

import solara
from pysepal.solara.notifications import use_notifications

from component.message import msg
from mgci.infrastructure.areas import prepare_biobelt

log = logging.getLogger('MGCI.solara.areas')


@solara.component
def BiobeltOverlay(config, map_, gee_interface, on_legend):
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
    solara.use_effect(clear, [identity])

    def receive():
        if task.finished and task.value is not None:
            captured, payload, error = task.value
            if captured != identity:
                return
            if error:
                notifications.error(error)
                return
            import ee
            from pysepal.mapping.layer import EELayer
            map_.add_layer(EELayer(ee_object=ee.Image(ee.deserializer.decode(json.loads(payload['graph']))),
                                  url=payload['url'], name=msg('layers.biobelts'), attribution='Google Earth Engine', max_zoom=24), key='biobelts')
            on_legend(payload['legend'])
    solara.use_effect(receive, [task.finished, task.value])
    solara.use_effect(lambda: lambda: map_.remove_layer('biobelts', none_ok=True), [])
