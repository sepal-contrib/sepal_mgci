from datetime import datetime as dt
from pathlib import Path
from typing import Dict, List, Optional, Union

import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
import traitlets as t
from sepal_ui import mapping as sm
from sepal_ui.aoi.aoi_model import AoiModel
from sepal_ui.aoi.aoi_view import AoiView
from sepal_ui.message import ms
from sepal_ui.scripts import decorator as sd
from sepal_ui.scripts import utils as su
from typing_extensions import Self

from component.scripts.biobelt import add_belt_map


class AoiView(AoiView):
    """Custom AOI view to add the biobelt map after the AOI selection."""

    @sd.loading_button(debug=True)
    def _update_aoi(self, *args) -> Self:
        """load the object in the model & update the map (if possible)."""
        # read the information from the geojson datas
        if self.map_:
            self.model.geo_json = self.aoi_dc.to_json()

        # update the model
        self.model.set_object()
        self.alert.add_msg(ms.aoi_sel.complete, "success")

        # update the map
        if self.map_:
            self.map_.remove_layer("aoi", none_ok=True)
            self.map_.zoom_bounds(self.model.total_bounds())
            self.map_.add_layer(self.model.get_ipygeojson(self.map_style))

            self.aoi_dc.hide()

        add_belt_map(self.model, self.map_)

        # tell the rest of the apps that the aoi have been updated
        self.updated += 1

        return self
