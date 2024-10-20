import traitlets as t
from sepal_ui.aoi.aoi_model import AoiModel
from sepal_ui.aoi.aoi_view import AoiView
from sepal_ui.message import ms
from sepal_ui.scripts import decorator as sd
from typing_extensions import Self
from component.widget.legend_control import LegendControl
from component.scripts.biobelt import get_belt_area
from component.parameter.module_parameter import BIOBELT, BIOBELT_LEGEND, BIOBELT_VIS
from component.scripts.thread_controller import TaskController
from component.widget.legend_control import LegendControl
import ee
from component.message import cm
from copy import deepcopy


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
            self.map_.remove_all()
            self.map_.legend.hide()
            self.model.geo_json = self.aoi_dc.to_json()

        # update the model
        self.model.set_object()

        # update the map
        if self.map_:
            self.map_.zoom_bounds(self.model.total_bounds())
            self.map_.add_layer(self.model.get_ipygeojson(self.map_style))
            self.aoi_dc.hide()

        self.add_belt_map(self.model, self.map_)
        self.alert.add_msg(ms.aoi_sel.complete, "success")

        # tell the rest of the apps that the aoi have been updated
        self.updated += 1

        return self

    def add_belt_map(self, aoi_model, map_):
        """Create and display bioclimatic belt layer on a map."""

        def _update_legend(result):
            """Update the legend with the biobelt map data."""
            try:
                legend_dict, _ = result
                print("Updating legend...")
                legend.legend_dict = {}
                legend.legend_dict = deepcopy(legend_dict)
            except Exception as e:
                legend.set_error(f"Failed to update legend: {e}")

            finally:
                legend.loading = False

        try:
            map_.zoom = 10
            map_.center = [0, 0]

            aoi = aoi_model.feature_collection.geometry().simplify(1000)
            map_.zoom_ee_object(aoi.bounds())
            biobelt = ee.Image(BIOBELT).clip(aoi)
            map_.addLayer(biobelt, BIOBELT_VIS, cm.aoi.legend.belts)

        except Exception as e:

            raise Exception(f"Failed to add biobelt map: {e}")

        finally:

            try:

                legend = map_.legend
                legend.loading = True

                task_controller = TaskController(
                    function=get_belt_area,
                    aoi=aoi,
                    biobelt=biobelt,
                    callback=_update_legend,
                    disable_components=[self],
                )

                task_controller.start_task()

                print("Biobelt map added.")

            except Exception as e:

                legend.set_error(f"Failed to update legend: {e}")

            finally:

                legend.loading = False
