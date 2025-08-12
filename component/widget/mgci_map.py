import ipyvuetify as v
from ipyleaflet import WidgetControl

from sepal_ui import mapping as m
from sepal_ui.mapping import InspectorControl
from sepal_ui.mapping.map_btn import MapBtn

import component.widget as cw
from component.message import cm

__all__ = ["MgciMap"]


class MgciMap(m.SepalMap):
    def __init__(self, gee_interface, theme_toggle, *args, **kwargs):

        kwargs["fullscreen"] = True
        kwargs["dc"] = False
        kwargs["min_zoom"] = 3
        kwargs["gee"] = True

        default_basemap = (
            "CartoDB.DarkMatter" if v.theme.dark is True else "CartoDB.Positron"
        )

        basemaps = [default_basemap] + ["SATELLITE"]

        super().__init__(
            *args,
            theme_toggle=theme_toggle,
            basemaps=basemaps,
            gee_interface=gee_interface,
            **kwargs
        )

        # inspector_control = InspectorControl(self)
        # self.add_control(inspector_control)
