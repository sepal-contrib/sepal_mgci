import ipyvuetify as v

from pathlib import Path

import ee
from component.scripts.gee import get_gee_recipe_folder
from sepal_ui import sepalwidgets as sw
from sepal_ui.scripts import utils as su
from sepal_ui.scripts.drive_interface import GDriveInterface
from sepal_ui.scripts.gee_interface import GEEInterface

import component.scripts as cs
from component.message import cm
from component.model.model import MgciModel
from component.scripts.layers import get_layer_a, get_layer_b


class ExportMapDialog(v.Dialog):
    def __init__(
        self,
        model: MgciModel,
        w_layers,
        alert: sw.Alert,
        gee_interface=None,
    ):
        super().__init__()

        self.model = model
        self.gee_interface = gee_interface
        self.alert = alert

        self.items = []
        self.max_width = "700px"
        self.v_model = False

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
        gdrive = sw.Radio(label=cm.map.dialog.export.radio.gdrive, value="gdrive")
        self.w_method = sw.RadioGroup(
            v_model="gee", row=True, children=[sepal, gee, gdrive]
        )
        self.w_layers = w_layers

        # add btn component for the loading_button
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

        else:
            raise Exception("No valid layer selected")

        layer_name = selection[2].replace(" ", "").lower()
        prefix = "SubA" if selection[0] == "a" else "SubB"

        return layer, vis_params, f"{prefix}_{layer_name}"

    @su.loading_button()
    def on_download(self, *_):
        """download the dataset using the given parameters."""
        aoi = self.model.aoi_model.feature_collection

        if not aoi:
            raise Exception(cm.error.no_aoi)

        # The value from the w_layers is a tuple with (theme, id_)
        ee_image, vis_params, layer_name = self.get_ee_image(*self.w_layers.v_model)

        folder_name = f"{self.model.aoi_model.name}_{self.model.session_id}"
        layer_name = f"{layer_name}"

        export_params = {
            # "image": ee_image,
            "description": layer_name,
            "scale": self.w_scale.v_model,
            "region": aoi.geometry(),
            "max_pixels": 1e13,
        }

        # launch the task
        if self.w_method.v_model == "gee":

            recipe_gee_folder = get_gee_recipe_folder(folder_name, self.gee_interface)
            asset_id = str(recipe_gee_folder / layer_name)
            export_params.update(asset_id=asset_id)
            self.gee_interface.export_image_to_asset(ee_image, **export_params)

            msg = sw.Markdown(cm.map.dialog.export.gee_task_success.format(asset_id))
            self.alert.add_msg(msg, "success")

        elif self.w_method.v_model == "gdrive":

            self.gee_interface.export_image_to_drive(ee_image, **export_params)
            msg = sw.Markdown(cm.map.dialog.export.gee_task_success.format(layer_name))
            self.alert.add_msg(msg, "success")

        elif self.w_method.v_model == "sepal":
            # TODO: Create the method to export using sepal
            pass

    def open_dialog(self, *_):
        """Open dialog and disable the layers widget for display only."""
        # Disable the layers widget and make it full width when dialog opens

        if not self.model.aoi_model.feature_collection:
            self.alert.add_msg(cm.error.no_aoi, "error")
            raise Exception(cm.error.no_aoi)

        selection = self.w_layers.v_model
        if not selection:
            self.alert.add_msg(cm.error.no_aoi, "error")
            raise Exception("No layer selected")

        self.w_layers.disabled = True
        self.w_layers.style_ = "width: 100%"
        self.v_model = True

    def close_dialog(self, *_):
        """Close dialog and restore the layers widget to active state."""
        # Re-enable the layers widget when dialog closes
        self.w_layers.disabled = False
        self.w_layers.style_ = "max-width: 362px"
        self.v_model = False
