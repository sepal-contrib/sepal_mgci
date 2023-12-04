from ipyleaflet import WidgetControl
import ipyvuetify as v

import sepal_ui.sepalwidgets as sw
from sepal_ui.mapping import SepalMap
from sepal_ui.mapping.map_btn import MapBtn
from sepal_ui.mapping import InspectorControl
import sepal_ui.scripts.decorator as su


from component.model.model import MgciModel
import component.parameter.visualization as visuals
from component.scripts.layers import get_layer_a, get_layer_b
from component.widget.export_dialog import ExportMapDialog
from component.widget.legend_control import LegendControl


class LayerHandler(sw.Card):
    def __init__(self, map_: SepalMap, model: MgciModel):
        self.width = "450px"
        self.map_ = map_

        self.map_.add_legend(
            "lc_legend", "Land cover", visuals.LEGENDS["land_cover"], vertical=False
        )
        self.map_.add_legend(
            "deg_legend", "Degradation", visuals.LEGENDS["degradation"]
        )

        self.class_ = "d-block pa-2"
        self.model = model

        super().__init__()
        self.sub_a_items = []
        self.sub_b_items = []

        self._layers = []

        self.w_layers = sw.Select(
            items=[],
            v_model=[],
            label="Layers",
        )
        self.alert = sw.Alert()
        self.btn = sw.Btn("", gliph="mdi-plus")

        self.children = [v.Flex(class_="d-flex", children=[self.w_layers, self.btn])]

        self.btn.on_event("click", self.add_layer)
        self.model.observe(self.update_layer_list, "sub_a_year")
        self.model.observe(self.update_layer_list, "sub_b_year")

        # Get with the default values
        self.update_layer_list({"owner": "sub_a_year", "new": self.model.sub_a_year})
        self.update_layer_list({"owner": "sub_b_year", "new": self.model.sub_b_year})

    def update_layer_list(self, change):
        """Update w_layers with the layers selected by the user"""

        # I need two sublists, one for each subindicator

        # First check if both "year" and "asset" are not empty on all model.sub_a_year.values()

        subindicator = change["owner"]
        data = change["new"]

        if subindicator == "sub_a_year":
            if all([year.get("year") and year.get("asset") for year in data.values()]):
                self.sub_a_items = [{"header": "Sub indicator A"}] + [
                    {"text": year.get("year"), "value": ["a", year.get("asset")]}
                    for year in data.values()
                ]

        if subindicator == "sub_b_year":
            baseline = data.get("baseline", {}).values()
            report = {k: v for k, v in data.items() if k != "baseline"}.values()

            if all(
                [
                    all(val.get("asset") for val in baseline) if baseline else False,
                    all(val.get("year") for val in baseline) if baseline else False,
                    all(val.get("asset") for val in report) if report else False,
                    all(val.get("year") for val in report) if report else False,
                ]
            ):
                # Create a list of all possible layers that can be shown

                # Total degradation for baseline against all report years
                # Baseline degradation (2000-2015)
                # Report degradation for all years (2015-xxx)
                # Land cover for all years (2000-xxx)

                self.sub_b_items = (
                    [{"header": "Sub indicator B"}]
                    + [
                        {
                            "text": f"Total degradation {year}",
                            "value": ["b", f"final_degradation_{year}"],
                        }
                        for year in [y["year"] for y in report]
                    ]
                    + [
                        {
                            "text": "Baseline degradation",
                            "value": ["b", "baseline_degradation"],
                        }
                    ]
                    + [
                        {
                            "text": f"Report degradation {year}",
                            "value": ["b", f"report_degradation_{year}"],
                        }
                        for year in [y["year"] for y in report]
                    ]
                    + [
                        {
                            "text": f"Land cover {year}",
                            "value": ["b", f"land_cover_{year}"],
                        }
                        for year in [y["year"] for y in baseline]
                    ]
                    + [
                        {
                            "text": f"Land cover {year}",
                            "value": ["b", f"report_year_{year}"],
                        }
                        for year in [y["year"] for y in report]
                    ]
                )

        if self.sub_a_items and self.sub_b_items:
            self.w_layers.items = self.sub_a_items + self.sub_b_items

        else:
            self.w_layers.items = ["Some layers are missing"]

    @su.loading_button()
    def add_layer(self, *_):
        """Get the layers from the model"""

        selection = self.w_layers.v_model

        aoi = self.model.aoi_model.feature_collection.geometry()

        if selection[0] == "a":
            remap_matrix = self.model.matrix_sub_a
            layer, vis_params = get_layer_a(selection[1], remap_matrix, aoi)

        elif selection[0] == "b":
            remap_matrix = self.model.matrix_sub_b
            sub_b_year = self.model.sub_b_year
            transition_matrix = self.model.transition_matrix

            layer, vis_params = get_layer_b(
                selection[1], remap_matrix, aoi, sub_b_year, transition_matrix
            )

        self.map_.addLayer(layer, vis_params, selection[1])
        self.map_.centerObject(aoi)


class Map(SepalMap):
    """Custom Map"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add_class("results_map")

    def add_legend(
        self,
        id_,
        title: str = "Legend",
        legend_dict: dict = {},
        position: str = "bottomright",
        vertical: bool = True,
    ) -> None:
        """Creates and adds a custom legend as widget control to the map.

        Args:
            title: Title of the legend. Defaults to 'Legend'.
            legend_dict: dictionary with key as label name and value as color
            position: the position (corners) of the legend on the map
            vertical: vertical or horizoal position of the legend
        """
        # Define as class member so it can be accessed from outside.
        self.legend = LegendControl(
            legend_dict,
            title=title,
            vertical=vertical,
            position=position,
            attributes={"id": id_},
        )

        return self.add(self.legend)


class MapView(sw.Card):
    def __init__(self, model: MgciModel):
        super().__init__()
        self.model = model

        self.map_ = Map()
        inspector_control = InspectorControl(self.map_)

        btn = MapBtn(content="mdi-download")

        download_control = WidgetControl(widget=btn, position="topleft")

        layer_handler = LayerHandler(self.map_, self.model)
        layer_control = WidgetControl(widget=layer_handler, position="topleft")

        self.map_.add_control(layer_control)
        self.map_.add_control(download_control)
        self.map_.add_control(inspector_control)

        self.export_dialog = ExportMapDialog(self.model, layer_handler.w_layers)

        self.children = [self.export_dialog, self.map_]

        btn.on_event("click", self.export_dialog.open_dialog)
