from eeclient.client import EESession

import ipyvuetify as v

import sepal_ui.sepalwidgets as sw
from sepal_ui.mapping import SepalMap
from sepal_ui.sepalwidgets.btn import TaskButton
from sepal_ui.solara import get_current_gee_interface

from component.model.model import MgciModel
from component.scripts.layers import get_layer_a, get_layer_b
from component.widget.export_dialog import ExportMapDialog
from component.widget.legend_control import LegendDashboard
from component.message import cm


class LayerHandler(sw.Layout):
    def __init__(self, map_: "Map", model: MgciModel, alert: sw.Alert = None):
        self.map_ = map_

        self.alert = alert or sw.Alert()

        # self.map_.add_legend(
        #     "lc_legend", "Land cover", visuals.LEGENDS["land_cover"], vertical=False
        # )
        # self.map_.add_legend(
        #     "deg_legend", "Degradation", visuals.LEGENDS["degradation"]
        # )

        self.class_ = "d-block pa-2"
        self.model = model

        super().__init__()
        self.sub_a_items = []
        self.sub_b_items = []

        self._layers = []

        self.w_layers = sw.Select(
            style_="max-width: 362px",
            items=[],
            v_model=[],
            label="Layers",
        )

        self.btn = TaskButton("Add layer", small=True, block=True)

        # Create export button and dialog
        self.btn_export = sw.Btn("Export layer", small=True, block=True)
        self.export_dialog = ExportMapDialog(
            model=self.model,
            w_layers=self.w_layers,
            alert=self.alert,
            gee_interface=get_current_gee_interface(),
        )

        self.children = [
            v.Col(children=[self.w_layers]),
            v.Col(children=[self.btn], class_="pt-0"),
            v.Col(children=[self.btn_export], class_="pt-2"),
            self.export_dialog,
        ]

        self.model.observe(self.update_layer_list, "sub_a_year")
        self.model.observe(self.update_layer_list, "sub_b_year")

        # Get with the default values
        self.update_layer_list({"name": "sub_a_year", "new": self.model.sub_a_year})
        self.update_layer_list({"name": "sub_b_year", "new": self.model.sub_b_year})

        self._configure_task_button()

        # Configure export button
        self.btn_export.on_event("click", self.export_dialog.open_dialog)

    def update_layer_list(self, change):
        """Update w_layers with the layers selected by the user"""

        # I need two sublists, one for each subindicator
        # either case, remove all layers from map
        self.map_.remove_all(keep_names=["AOI", cm.aoi.legend.belts])

        # First check if both "year" and "asset" are not empty on all model.sub_a_year.values()
        subindicator = change["name"]
        data = change["new"]

        if subindicator == "sub_a_year":
            vals = [
                year.get("year", None) and year.get("asset", None)
                for year in data.values()
            ]

            if all(vals) and vals != []:
                self.sub_a_items = [{"header": cm.layers.sub_a_header}] + [
                    {
                        "text": year.get("year"),
                        "value": [
                            "a",
                            year.get("asset"),
                            f"{cm.layers.land_cover} {year.get('year')}",
                        ],
                    }
                    for year in data.values()
                ]
            else:
                self.sub_a_items = []

        if subindicator == "sub_b_year":
            baseline = data.get("baseline", {}).values()
            report = {k: v for k, v in data.items() if k != "baseline"}.values()

            vals = [
                all(val.get("asset") for val in baseline) if baseline else False,
                all(val.get("year") for val in baseline) if baseline else False,
                all(val.get("asset") for val in report) if report else False,
                all(val.get("year") for val in report) if report else False,
            ]

            if all(vals) and vals != []:
                # Create a list of all possible layers that can be shown

                # Total degradation for baseline against all report years
                # Baseline degradation (2000-2015)
                # Report degradation for all years (2015-xxx)
                # Land cover for all years (2000-xxx)

                self.sub_b_items = (
                    [{"header": cm.layers.sub_b_header}]
                    + [
                        {
                            "text": f"{cm.layers.final_degradation} {year}",
                            "value": [
                                "b",
                                f"final_degradation_{year}",
                                f"{cm.layers.final_degradation} {year}",
                            ],
                        }
                        for year in [y["year"] for y in report]
                    ]
                    + [
                        {
                            "text": cm.layers.baseline_degradation,
                            "value": [
                                "b",
                                "baseline_degradation",
                                cm.layers.baseline_degradation,
                            ],
                        }
                    ]
                    + [
                        {
                            "text": f"{cm.layers.report_degradation} {year}",
                            "value": [
                                "b",
                                f"report_degradation_{year}",
                                f"{cm.layers.report_degradation} {year}",
                            ],
                        }
                        for year in [y["year"] for y in report]
                    ]
                    + [
                        {
                            "text": f"{cm.layers.land_cover} {year}",
                            "value": [
                                "b",
                                f"land_cover_{year}",
                                f"{cm.layers.land_cover} {year}",
                            ],
                        }
                        for year in [y["year"] for y in baseline]
                    ]
                    + [
                        {
                            "text": f"{cm.layers.land_cover} {year}",
                            "value": [
                                "b",
                                f"land_cover_{year}",
                                f"{cm.layers.land_cover} {year}",
                            ],
                        }
                        for year in [y["year"] for y in report]
                    ]
                )
            else:
                self.sub_b_items = []

        if self.sub_a_items or self.sub_b_items:
            self.w_layers.items = self.sub_a_items + self.sub_b_items

        else:
            self.w_layers.items = []

    def _configure_task_button(self):
        """Configure the task button to add the layer"""
        gee_interface = get_current_gee_interface()

        def add_layer():
            def callback(*args):
                pass

            return gee_interface.create_task(
                func=self.add_layer_async,
                key="add_layer",
                on_done=callback,
                on_error=lambda e: self.alert.add_msg(str(e), type_="error"),
            )

        self.btn.configure(task_factory=add_layer)

    async def add_layer_async(self, *_):
        """Get the layers from the model

        Args:
            selection: the selection from the w_layers widget
        """
        if not self.model.aoi_model.feature_collection:
            raise Exception(cm.error.no_aoi)

        selection = self.w_layers.v_model

        if not selection:
            raise Exception("No layer selected")

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

        else:
            raise Exception("No valid layer selected")

        coords = await self.map_.gee_interface.get_info_async(
            aoi.bounds().coordinates().get(0)
        )
        self.map_.zoom_bounds((*coords[0], *coords[2]))

        await self.map_.add_ee_layer_async(
            layer, vis_params=vis_params, name=selection[2]
        )


class Map(SepalMap):
    """Custom Map"""

    def __init__(self, gee_interface: EESession, **kwargs):
        default_basemap = (
            "CartoDB.DarkMatter" if v.theme.dark is True else "CartoDB.Positron"
        )
        basemaps = [default_basemap] + ["SATELLITE"]

        super().__init__(basemaps=basemaps, gee_interface=gee_interface, **kwargs)

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
        self.legend = LegendDashboard(
            legend_dict=legend_dict,
            title=title,
            vertical=vertical,
            position=position,
            attributes={"id": id_},
        )

        return self.add(self.legend)
