from component.scripts.logger import setup_logging
from component.widget.custom_widgets import AlertDialog

setup_logging()

import solara
import solara.server.settings
from solara.lab.components.theming import theme
from sepal_ui.scripts.utils import init_ee
from sepal_ui.sepalwidgets.vue_app import ThemeToggle
from sepal_ui.sepalwidgets.vue_app import MapApp
import sepal_ui.sepalwidgets as sw
from sepal_ui.solara import (
    setup_sessions,
    with_sepal_sessions,
    get_current_gee_interface,
    get_current_sepal_client,
    get_current_drive_interface,
    setup_theme_colors,
    get_session_info,
)

from component.tile.calculation_tile import CalculationView
from component.tile.dashboard_tile import DashViewA, DashViewB
from component.tile.vegetation_tile import VegetationTile
from component.tile.aoi_tile import AoiView
from component.tile.task_tile import DownloadTaskView
from component.model import MgciModel
from component.message import cm
from component.widget.mgci_map import MgciMap
from component.parameter.directory import initialize_remote
from component.widget.map import LayerHandler

import logging

logger = logging.getLogger("MGCI")
logger.debug("Starting MGCI application...")
init_ee()


@solara.lab.on_kernel_start
def init_gee():
    return setup_sessions()


solara.server.settings.assets.fontawesome_path = (
    "/@fortawesome/fontawesome-free@6.7.2/css/all.min.css"
)
solara.server.settings.assets.extra_locations = ["./assets/"]
solara.server.settings.kernel.cull_timeout = "0s"


@solara.component
@with_sepal_sessions(module_name="sdg_indicators/15.4.2")
def Page():

    setup_theme_colors()
    theme_toggle = ThemeToggle()
    theme_toggle.observe(lambda e: setattr(theme, "dark", e["new"]), "dark")

    # This is for the secondary panel
    alert = sw.Alert(class_="mt-0 mx-4")
    AlertDialog.element(w_alert=alert)

    gee_interface = get_current_gee_interface()
    drive_interface = get_current_drive_interface()
    sepal_client = get_current_sepal_client()

    logger.debug(
        f"THIS IS THE GEE INTERFACE IM PASSING TO COMPONENTS {id(gee_interface)}..."
    )

    initialize_remote(sepal_client)

    map_ = MgciMap(gee_interface=gee_interface, theme_toggle=theme_toggle)
    logger.debug("Map initialized")
    aoi_view = AoiView(map_=map_)
    logger.debug("AOI view initialized")
    model = MgciModel(aoi_view.model, sepal_client=sepal_client)
    logger.debug("Model initialized")
    vegetation_tile = VegetationTile(
        model=model, aoi_model=model.aoi_model, sepal_client=sepal_client, alert=alert
    )
    logger.debug(model)
    logger.debug("Vegetation tile initialized")
    calculation_tile = CalculationView(
        model=model,
        units="sqkm",
        rsa=True,
        sepal_client=sepal_client,
        gee_interface=gee_interface,
    )
    logger.debug(model)
    logger.debug("Calculation tile initialized")
    logger.debug("Dashboard tile initialized")
    task_tile = DownloadTaskView(
        sepal_client=sepal_client,
        drive_interface=drive_interface,
        gee_interface=gee_interface,
    )
    logger.debug("Task tile initialized")

    layer_handler = LayerHandler(map_, model, alert=alert)
    dash_view_a = DashViewA(model, alert=alert)
    dash_view_b = DashViewB(model, alert=alert)

    # Debug button to log MGCI model
    def log_mgci_model():
        logger.debug(f"{model}")

    debug_button = solara.Button("Debug MGCI Model", on_click=log_mgci_model)

    steps_data = [
        {
            "id": 2,
            "name": cm.app.drawer_item.aoi,
            "icon": "mdi-map-marker-check",
            "display": "dialog",
            "content": aoi_view,
        },
        {
            "id": 3,
            "name": cm.app.drawer_item.vegetation,
            "icon": "mdi-pine-tree",
            "display": "dialog",
            "content": vegetation_tile,
        },
        {
            "id": 4,
            "name": cm.app.drawer_item.calculation,
            "icon": "mdi-cogs",
            "display": "dialog",
            "content": calculation_tile,
        },
        {
            "id": 5,
            "name": cm.app.drawer_item.dashboard,
            "icon": "mdi-view-dashboard",
            "display": "dialog",
            "content": [],
            "right_panel_action": "toggle",  # "open", "close", "toggle", or None
        },
        {
            "id": 6,
            "name": cm.app.drawer_item.task,
            "icon": "mdi-export",
            "display": "dialog",
            "content": task_tile,
        },
    ]

    extra_content_config = {
        "title": "Results",
        "icon": "mdi-image-filter-hdr",
        "width": 400,
        "description": "This section contains the results of the analysis. You can add layers to the map, view sub-indicators, and download tasks.",
        "toggle_icon": "mdi-chart-line",
    }

    extra_content_data = [
        {
            "title": "Visualize and export layers",
            "icon": "mdi-layers",
            "content": [layer_handler],
            "description": "To add layers to the map, you will first need to select the area of interest and the years in the 3. Indicator settings step.",
        },
        {
            "content": [dash_view_a],
            "title": "Sub indicator A",
            "icon": "mdi-chart-bar",
        },
        {
            "content": [dash_view_b],
            "title": "Sub indicator B",
            "icon": "mdi-chart-bar",
        },
        {
            "title": "Debug Tools",
            "icon": "mdi-bug",
            "content": [debug_button],
            "description": "Debug tools for development and troubleshooting.",
        },
    ]

    MapApp.element(
        app_title="SDG 15.4.2",
        app_icon="mdi-image-filter-hdr",
        main_map=[map_],
        steps_data=steps_data,
        extra_content_config=extra_content_config,
        extra_content_data=extra_content_data,
        theme_toggle=[theme_toggle],
        dialog_width=750,
        repo_url="https://github.com/sepal-contrib/sepal_mgci",
    )

    sessions = get_session_info()
    logger.debug(f"Current sessions: {sessions}")

    logger.debug(model)
