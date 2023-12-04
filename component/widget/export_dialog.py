import ipyvuetify as v

from pathlib import Path

import ee
from sepal_ui import sepalwidgets as sw
from sepal_ui.scripts import utils as su

from component.message import cm
from component.model.model import MgciModel
from component.scripts.layers import get_layer_a, get_layer_b
from component.widget.base_dialog import BaseDialog

ee.Initialize()


class ExportMapDialog(v.Dialog):
    def __init__(self, model: MgciModel, w_layers):
        super().__init__()

        self.model = model
        self.items = []
        self.max_width = "700px"

        # create the useful widgets
        # align on the landsat images
        w_scale_lbl = sw.Html(tag="h4", children=["Scale"])
        self.w_scale = sw.Slider(
            v_model=1000, min=10, max=2000, thumb_label="always", step=10
        )

        w_method_lbl = sw.Html(tag="h4", children=[cm.map.dialog.export.radio.label])
        sepal = sw.Radio(
            label=cm.map.dialog.export.radio.sepal, value="sepal", disabled=True
        )
        gee = sw.Radio(label=cm.map.dialog.export.radio.gee, value="gee")
        self.w_method = sw.RadioGroup(v_model="gee", row=True, children=[sepal, gee])
        self.w_layers = w_layers

        # add alert and btn component for the loading_button
        self.alert = sw.Alert()
        self.btn = sw.Btn(cm.map.dialog.export.export, small=True)
        self.btn_cancel = sw.Btn(cm.map.dialog.export.cancel, small=True)

        title = sw.CardTitle(children=["Export map"])

        text = sw.CardText(
            children=[
                self.w_layers,
                w_scale_lbl,
                self.w_scale,
                w_method_lbl,
                self.w_method,
                self.alert,
            ]
        )
        actions = sw.CardActions(
            children=[
                sw.Spacer(),
                self.btn,
                self.btn_cancel,
            ]
        )

        self.children = [sw.Card(children=[title, text, actions])]

        # add js behaviour
        self.btn.on_event("click", self.on_download)
        self.btn_cancel.on_event("click", self.close_dialog)

    def get_ee_image(self, *_) -> ee.Image:
        selection = self.w_layers.v_model

        aoi = self.model.aoi_model.feature_collection

        if not aoi:
            raise Exception(cm.error.no_aoi)

        if selection[0] == "a":
            remap_matrix = self.model.matrix_sub_a
            layer, vis_params = get_layer_a(selection[1], remap_matrix, aoi.geometry())

        elif selection[0] == "b":
            remap_matrix = self.model.matrix_sub_b
            sub_b_year = self.model.sub_b_year
            transition_matrix = self.model.transition_matrix

            layer, vis_params = get_layer_b(
                selection[1],
                remap_matrix,
                aoi.geometry(),
                sub_b_year,
                transition_matrix,
            )

        return layer, vis_params

    @su.loading_button()
    def on_download(self, *_):
        """download the dataset using the given parameters."""
        aoi = self.model.aoi_model.feature_collection

        if not aoi:
            raise Exception(cm.error.no_aoi)

        # The value from the w_layers is a tuple with (theme, id_)
        ee_image, vis_params = self.get_ee_image(*self.w_layers.v_model)
        name = "test_name"
        export_params = {
            "image": ee_image,
            "description": name,
            "scale": self.w_scale.v_model,
            "region": aoi.geometry(),
            "maxPixels": 1e13,
        }

        # launch the task
        if self.w_method.v_model == "gee":
            folder = Path(ee.data.getAssetRoots()[0]["id"])
            export_params.update(assetId=str(folder / name), description=f"{name}_gee")
            task = ee.batch.Export.image.toAsset(**export_params)
            task.start()
            msg = sw.Markdown(cm.map.dialog.export.gee_task_success.format(name))
            self.alert.add_msg(msg, "success")

        elif self.w_method.v_model == "sepal":
            # TODO: Create the method to export using sepal
            pass

    def open_dialog(self, *_):
        """Open dialog."""
        self.v_model = True

    def close_dialog(self, *_):
        """Close dialog."""
        self.v_model = False
