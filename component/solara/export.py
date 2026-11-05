"""Results "Export" section: pysepal's export dialog over every MGCI layer."""

import solara
from pysepal.solara.components.export import ExportLauncher

from mgci.infrastructure.layers import export_sources
from component.message import msg


@solara.component
def ExportPanel(state, gee_interface, drive_interface, sepal_client, enabled=None):
    # Like the layer selector, offer only the indicators switched on in the settings.
    indicators = ('a', 'b') if enabled is None else enabled.value
    sources = export_sources(state.configuration, indicators, state.session_id)
    ExportLauncher(sources=sources, label=msg('layers.export'), dialog_title=msg('layers.export_title'),
                   button_text=True, block=True, gee_interface=gee_interface,
                   drive_interface=drive_interface, sepal_client=sepal_client)
