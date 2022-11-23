from pathlib import Path

import ipyvuetify as v
import pandas as pd
import sepal_ui.scripts.utils as su
from sepal_ui import sepalwidgets as sw
from sepal_ui.message import ms
from sepal_ui.reclassify.parameters import *
from traitlets import link

import component.parameter.module_parameter as param
from component.message import cm
from component.widget import reclassify as rec

__all__ = ["ReclassifyTile"]


class ReclassifyTile(sw.Card):

    """Custom reclassify tile to replace the default Reclassify Tile and View
    from sepal_ui. This card will change depending on a input questionaire which
    aims to create a custom view depending on their answers.

    Args:
        questionaire (Questionaire card): Vegetation Tile Questionaire
    """

    def __init__(
        self,
        questionaire,
        results_dir=Path.home() / "downloads",
        gee=True,
        dst_class=None,
        default_class={},
        aoi_model=None,
        folder=None,
        save=False,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        # output directory
        self.results_dir = Path(results_dir)

        self.aoi_model = aoi_model
        self.questionaire = questionaire

        # create the model
        self.model = rec.ReclassifyModel(
            dst_dir=self.results_dir,
            gee=gee,
            aoi_model=self.aoi_model,
            folder=folder,
            save=save,
            enforce_aoi=True,
        )

        # set the tabs elements
        self.w_reclass = rec.ReclassifyView(
            self.model,
            out_path=self.results_dir,
            gee=gee,
            default_class=default_class,
            aoi_model=aoi_model,
            folder=folder,
            enforce_aoi=True,
        ).nest_tile()

        # Create a default destination classification file

        self.w_reclass.w_dst_class_file.select_file(default_class["IPCC"]).hide()
        self.w_reclass.model.dst_class_file = default_class["IPCC"]
        self.w_reclass.model.dst_class = self.w_reclass.model.get_classes()

        self.load_btn = self.w_reclass.import_dialog.load_btn
        self.load_btn.disabled = True

        self.w_input_matrix = v.Row(
            class_="d-flex",
            align="center",
            children=[
                v.Col(cols="1", class_="text-right", children=[self.load_btn]),
            ],
        )

        # Insert the input map matrix widget in the reclassify view widget
        new_items = self.w_reclass.children.copy() + [self.w_input_matrix]
        self.w_reclass.children = new_items

        self.children = [
            self.w_reclass,
        ]

        self.get_view()
        self.questionaire.observe(self.get_view)
        self.w_reclass.model.observe(self.activate_load, "table_created")

    def activate_load(self, change):
        """Activate load matrix button once the user has created the table"""

        if change["new"]:
            self.load_btn.disabled = False
        else:
            self.load_btn.disabled = True

    def use_default(self):
        """Define a default asset to the w_image component from w_reclass"""

        self.w_reclass.model.matrix = dict(
            list(zip(*list(pd.read_csv(param.LC_MAP_MATRIX).to_dict("list").values())))
        )

    def get_view(self, change=None):
        """Observe the questionaire answers and display the proper view of the
        reclassify widget"""

        # get the reclassify view components
        components = [
            "w_dst_class_file",
            "w_input_title",
            "btn_get_table",
            "alert",
            "reclassify_table",
        ]

        # hide components
        for c in components:

            widget = getattr(self.w_reclass, c)
            widget.disabled = False
            su.hide_component(widget)

        self.w_input_matrix.class_ = "d-none"

        # Would you like to use a custom land use/land cover map?
        if self.questionaire.custom_lulc:

            self.w_reclass.w_ic_select.label = cm.reclass_view.ic_custom_label
            self.w_reclass.w_ic_select.disabled = False
            self.w_reclass.reclassify_table.set_table({}, {})
            components = ["btn_get_table", "reclassify_table"]

        else:
            components = []
            self.w_reclass.w_ic_select.label = cm.reclass_view.ic_default_label
            self.w_reclass.w_ic_select.v_model = param.LULC_DEFAULT
            self.w_reclass.w_ic_select.disabled = True
            self.use_default()

        # display components
        [su.show_component(getattr(self.w_reclass, c)) for c in components]
