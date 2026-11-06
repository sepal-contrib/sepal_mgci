"""MGCI application shell: session state, map and the step and results panels."""

import logging

import solara
from pysepal.mapping import SepalMap
from pysepal.solara import get_current_theme_state
from pysepal.solara.components.admin import AdminButton
from pysepal.solara.notifications import NotificationProvider

from component.message import messages, msg
from component.scripts.steps import add_step_actions
from component.widget.app_shell import MgciMapApp
from mgci.application.operations import prepare_request, refresh_transition
from mgci.application.state import ResourceState
from mgci.errors import LocalizedError
from mgci.infrastructure.defaults import initial_configuration
from mgci.infrastructure.transitions import load_transition
from mgci.infrastructure.workspace import ClientWorkspace
from .charts import ChartPanel
from .landcover import LandCoverPanel
from .layers import LayerPanel, MapOutputs
from .session import use_session_state
from .settings import SettingsPanel
from .tasks import TaskPanel
from .areas import BiobeltOverlay
from .aoi import AreaPanel
from . import toasts  # noqa: F401  (sets the toast timing on import)


@solara.component
def MgciApp(gee_interface, sepal_client, drive_interface):
    initial = solara.use_memo(initial_configuration, [])
    state, publish = use_session_state(initial)
    resources = solara.use_memo(lambda: {key: ResourceState() for key in ('a', 'b', 'transition', 'b_classes')}, [])
    workspace = solara.use_memo(lambda: ClientWorkspace(sepal_client) if sepal_client else None, [id(sepal_client)])
    theme = get_current_theme_state()
    map_ = solara.use_memo(lambda: SepalMap(gee=True, gee_interface=gee_interface, fullscreen=True, dc=False,
                                          min_zoom=3, theme_state=theme,
                                          basemaps=['SEPAL_DARK' if theme.dark else 'SEPAL_LIGHT', 'SATELLITE']), [])
    solara.use_effect(lambda: map_.close, [map_])
    NotificationProvider()
    context_legend = solara.use_reactive(None)
    enabled = solara.use_reactive(('a', 'b'))
    # (indicator, selector) of the layers drawn on the map; the layers table toggles them.
    shown = solara.use_reactive(frozenset())
    # The belts row of the layers table toggles the overlay; a new AOI shows it again.
    belts_shown = solara.use_reactive(True)
    belts_status = solara.use_reactive(None)
    BiobeltOverlay(state.configuration, map_, gee_interface, context_legend.set, belts_shown, belts_status.set)
    MapOutputs(state, map_, context_legend.value, shown)

    async def load(path):
        if workspace is None:
            raise LocalizedError('workspace_transition')
        return await load_transition(workspace, path)

    async def prepare(indicator, purpose, selection):
        try:
            return await prepare_request(state, indicator, purpose, selection, load=load)
        finally:
            publish()

    async def before_export(artifacts):
        if any(artifact.request.slot[0] == 'b' for artifact in artifacts):
            try:
                await refresh_transition(state, load)
            finally:
                publish()
        for artifact in artifacts:
            state.export_artifact(artifact.request)

    steps = add_step_actions([
        {'id': 2, 'name': msg('app.drawer_item.aoi'), 'icon': 'mdi-map-marker-check', 'display': 'dialog',
         'content': [AreaPanel(state, publish, resources, map_, gee_interface)]},
        {'id': 3, 'name': msg('app.drawer_item.vegetation'), 'icon': 'mdi-pine-tree', 'display': 'dialog',
         'content': [LandCoverPanel(state, publish, resources, gee_interface, sepal_client, load, workspace)]},
        {'id': 4, 'name': msg('app.drawer_item.calculation'), 'icon': 'mdi-cogs', 'display': 'dialog',
         'content': [SettingsPanel(state, publish, gee_interface, workspace, prepare, before_export, enabled)]},
        {'id': 5, 'name': msg('app.drawer_item.dashboard'), 'icon': 'mdi-view-dashboard', 'display': 'dialog',
         'content': [], 'right_panel_action': 'toggle'},
        {'id': 6, 'name': msg('app.drawer_item.task'), 'icon': 'mdi-export', 'display': 'dialog',
         'content': [TaskPanel(state, publish, workspace, gee_interface, drive_interface, sepal_client)]},
    ])
    MgciMapApp.element(app_title=msg('app.title'), app_icon='mdi-image-filter-hdr', main_map=[map_],
        theme_state=theme, steps_data=steps, dialog_width=750, locales=messages.available_locales(),
        repo_url='https://github.com/sepal-contrib/sepal_mgci',
        docs_url='https://mgci-docs.readthedocs.io/en/latest/sepal/index.html',
        right_panel_config={'title': msg('app.results.title'), 'icon': 'mdi-image-filter-hdr', 'width': 440,
                            'description': msg('app.results.description'),
                            'toggle_icon': 'mdi-chart-line'},
        right_panel_content=[
            {'content': [AdminButton(logger_instance=logging.getLogger('MGCI'))]},
            {'title': msg('app.results.layers_title'), 'icon': 'mdi-layers',
             'content': [LayerPanel(state, publish, shown, gee_interface, drive_interface, sepal_client, prepare, enabled,
                                     belts_shown=belts_shown, belts_status=belts_status.value)],
             'description': msg('app.results.layers_description', step=msg('app.drawer_item.calculation'))},
            {'title': msg('calculation.sub_a.title'), 'icon': 'mdi-chart-bar',
             'content': [ChartPanel(state, publish, 'a', gee_interface, prepare, before_export, enabled)],
             'description': msg('app.results.sub_a_description')},
            {'title': msg('calculation.sub_b.title'), 'icon': 'mdi-chart-bar',
             'content': [ChartPanel(state, publish, 'b', gee_interface, prepare, before_export, enabled)],
             'description': msg('app.results.sub_b_description')},
        ])
