import traitlets as t
from sepal_ui.aoi.aoi_model import AoiModel
from sepal_ui.aoi.aoi_view import AoiView
from sepal_ui.message import ms
from sepal_ui.scripts import decorator as sd
from typing_extensions import Self
from component.widget.legend_control import LegendControl
from component.scripts.biobelt import add_belt_map


class AoiView(AoiView):
    """Custom AOI view to add the biobelt map after the AOI selection."""

    def __init__(self, **kwargs: dict):
        kwargs.update(
            {
                "methods": ["-POINTS", "-DRAW"],
                "class_": "d-block pa-2 py-4",
                "min_width": "462px",
                "max_width": "462px",
                # I have to add this to avoid an error that takes aoi kwargs as model kwargs
                "model": AoiModel(),
            }
        )

        super().__init__(**kwargs)

        # Define as class member so it can be accessed from outside.
        self.map_.legend = LegendControl({}, title="", position="bottomright")
        self.map_.add_control(self.map_.legend)

    @sd.loading_button()
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
