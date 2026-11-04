"""AOI step: pysepal's AoiView, with the selection checked against the SDG reporting countries."""

import logging
from dataclasses import replace

import solara
from pysepal.solara.components.aoi import AoiView
from pysepal.solara.notifications import use_notifications

from mgci.infrastructure.areas import area_metadata
from mgci.infrastructure.science import capture_aoi
from .messages import msg

log = logging.getLogger('MGCI.solara.aoi')

METHODS = ['ADMIN0', 'ADMIN1', 'ADMIN2', 'ASSET']


@solara.component
def AreaPanel(state, publish, resources, map_, gee_interface):
    notifications = use_notifications()
    clear = solara.use_ref(None)
    rejected = solara.use_reactive('')

    def choose(result):
        try:
            name, code = area_metadata(result)
        except ValueError:
            # GAUL also lists disputed areas that have no M49 code, so the report cannot name them.
            rejected.set(result.name)
            return
        identity, graph = capture_aoi(result.feature_collection) if result is not None else ('', '')
        state.edit(replace(state.configuration, aoi_identity=identity, aoi_graph=graph,
                           aoi_name=name, ref_area=code, aoi_label=result.name if result is not None else '',
                           a=replace(state.configuration.a, evidence=None),
                           b=replace(state.configuration.b, evidence=None)))
        # The transition file does not depend on the area; keep a selection in progress.
        for key in ('a', 'b', 'b_classes'):
            resources[key].begin('')
        publish()

    def reject():
        # Runs after AoiView's own success toast, so the error is the last word and the map is cleared.
        if rejected.value:
            log.warning('Rejected AOI outside the reporting countries: %s', rejected.value)
            notifications.error(msg('areas.not_reporting', name=rejected.value))
            rejected.set('')
            clear.current()
    solara.use_effect(reject, [rejected.value])

    AoiView(on_value=choose, methods=METHODS, map_=map_, gee=True, clear_ref=clear)
