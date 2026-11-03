from pysepal.logger import setup_logging

logger = setup_logging(logger_name="MGCI")

import solara
from pysepal.scripts.utils import init_ee
from pysepal.solara import (
    get_current_drive_interface,
    get_current_gee_interface,
    get_current_sepal_client,
    setup_sessions,
    setup_solara_server,
    setup_theme_colors,
    with_sepal_sessions,
)

from component.solara.app import MgciApp

init_ee()
setup_solara_server()


@solara.lab.on_kernel_start
def on_kernel_start():
    return setup_sessions()


@solara.component
@with_sepal_sessions(module_name="sdg_indicators/15.4.2")
def Page():
    setup_theme_colors()
    MgciApp(
        get_current_gee_interface(),
        get_current_sepal_client(),
        get_current_drive_interface(),
    )
