"""MGCI application shell: session state, map and the step and results panels."""

import logging

import solara
from pysepal.mapping import SepalMap
from pysepal.solara import get_current_theme_state
from pysepal.solara.components.admin import AdminButton
from pysepal.solara.notifications import TOAST_TIMEOUT_DEFAULTS, NotificationProvider, ToastType

from component.message import cm
from component.scripts.steps import add_step_actions
from component.widget.app_shell import MgciMapApp
from mgci.application.operations import prepare_request, refresh_transition
from mgci.application.state import ResourceState
from mgci.infrastructure.defaults import initial_configuration
from mgci.infrastructure.transitions import load_transition
from mgci.infrastructure.workspace import ClientWorkspace
from .charts import ChartPanel
from .landcover import LandCoverPanel
from .export import ExportPanel
from .layers import LayerPanel, MapOutputs
from .session import use_session_state
from .settings import SettingsPanel
from .tasks import TaskPanel
from .areas import BiobeltOverlay
from .aoi import AreaPanel


# Error toasts stay until the user clicks them; the others keep pysepal's 3 s.
TOAST_TIMEOUT_DEFAULTS[ToastType.ERROR] = None


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
    BiobeltOverlay(state.configuration, map_, gee_interface, context_legend.set)
    MapOutputs(state, map_, context_legend.value)

    async def load(path):
        if workspace is None:
            raise ValueError('An authenticated SEPAL workspace is required to read transition files')
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
        {'id': 2, 'name': cm.app.drawer_item.aoi, 'icon': 'mdi-map-marker-check', 'display': 'dialog',
         'content': [AreaPanel(state, publish, resources, map_, gee_interface)]},
        {'id': 3, 'name': cm.app.drawer_item.vegetation, 'icon': 'mdi-pine-tree', 'display': 'dialog',
         'content': [LandCoverPanel(state, publish, resources, gee_interface, sepal_client, load, workspace)]},
        {'id': 4, 'name': cm.app.drawer_item.calculation, 'icon': 'mdi-cogs', 'display': 'dialog',
         'content': [SettingsPanel(state, publish, gee_interface, workspace, prepare, before_export, enabled)]},
        {'id': 5, 'name': cm.app.drawer_item.dashboard, 'icon': 'mdi-view-dashboard', 'display': 'dialog',
         'content': [], 'right_panel_action': 'toggle'},
        {'id': 6, 'name': cm.app.drawer_item.task, 'icon': 'mdi-export', 'display': 'dialog',
         'content': [TaskPanel(state, publish, workspace, gee_interface, drive_interface, sepal_client)]},
    ])
    MgciMapApp.element(app_title='SDG 15.4.2', app_icon='mdi-image-filter-hdr', main_map=[map_],
        theme_state=theme, steps_data=steps, dialog_width=750,
        repo_url='https://github.com/sepal-contrib/sepal_mgci',
        right_panel_config={'title': 'Results', 'icon': 'mdi-image-filter-hdr', 'width': 400,
                            'description': 'This section contains the results of the analysis. You can add layers '
                                           'to the map, view sub-indicators, and download tasks.',
                            'toggle_icon': 'mdi-chart-line'},
        right_panel_content=[
            {'content': [AdminButton(logger_instance=logging.getLogger('MGCI'))]},
            {'title': 'Visualize layers', 'icon': 'mdi-layers',
             'content': [LayerPanel(state, publish, map_, gee_interface, drive_interface, sepal_client, prepare, before_export, enabled)],
             'description': 'To add layers to the map, you will first need to select the area of interest '
                            'and the years in the 3. Indicator settings step.'},
            {'title': 'Export', 'icon': 'mdi-export-variant',
             'content': [ExportPanel(state, gee_interface, drive_interface, sepal_client, enabled)],
             'description': 'Export the layers of both sub-indicators to Earth Engine, Google Drive or your '
                            'SEPAL workspace. Layers become available once their sub-indicator is set up.'},
            {'title': 'Sub indicator A', 'icon': 'mdi-chart-bar',
             'content': [ChartPanel(state, publish, 'a', gee_interface, prepare, before_export, enabled)],
             'description': 'Explore land-cover composition for Sub-indicator A by year and mountain belt.'},
            {'title': 'Sub indicator B', 'icon': 'mdi-chart-bar',
             'content': [ChartPanel(state, publish, 'b', gee_interface, prepare, before_export, enabled)],
             'description': 'Explore land-cover transitions by period and mountain belt.'},
        ])
