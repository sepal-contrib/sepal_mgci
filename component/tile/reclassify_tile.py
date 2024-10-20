from pathlib import Path

import pandas as pd
from sepal_ui import sepalwidgets as sw
from traitlets import directional_link
from component.model.model import MgciModel

import component.parameter.module_parameter as param
import component.parameter.directory as dir_
from component.widget import reclassify as rec
from component.message import cm
from component.scripts.scripts import map_matrix_to_dict


__all__ = ["ReclassifyTile"]


class ReclassifyTile(sw.Layout):
    """Custom reclassify tile to replace the default Reclassify Tile and View
    from sepal_ui. This card will change depending on a input questionnaire which
    aims to create a custom view depending on their answers."""

    def __init__(
        self,
        mgci_model: MgciModel,
        results_dir=Path.home() / "downloads",
        gee=True,
        dst_class=None,
        default_class={},
        aoi_model=None,
        folder=None,
        save=False,
        id_="",
        alert: sw.Alert = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        # output directory
        self.results_dir = Path(results_dir)
        self.attributes = {"id": f"reclassify_tile_{id_}"}
        self.mgci_model = mgci_model

        self.aoi_model = aoi_model
        self.alert = alert

        # create the model
        self.model = rec.ReclassifyModel(
            dst_dir=self.results_dir,
            gee=gee,
            aoi_model=self.aoi_model,
            folder=folder,
            save=save,
            enforce_aoi=True,
            dst_class_file=dir_.LOCAL_LC_CLASSES,
        )

        # set the tabs elements
        self.w_reclass = rec.ReclassifyView(
            self.model,
            out_path=dir_.MATRIX_DIR,
            gee=gee,
            default_class=default_class,
            aoi_model=aoi_model,
            folder=folder,
            enforce_aoi=True,
            id_=id_,
            alert=alert,
        )

        self.w_reclass.model.dst_class = self.model.get_classes()
        self.w_reclass.w_ic_select.label = cm.reclass_view.ic_custom_label

        self.children = [self.w_reclass]

        directional_link(
            (self.model, "src_gee"),
            (self.mgci_model, f"lc_asset_{id_}"),
        )

        directional_link(
            (self.model, "matrix"),
            (self.mgci_model, f"matrix_{id_}"),
        )

        directional_link(
            (self.model, "ic_items"),
            (self.mgci_model, f"ic_items_{id_}"),
        )

        directional_link(
            (self.model, "dst_class"),
            (self.mgci_model, f"lulc_classes_{id_}"),
        )

        self.use_default()

    def use_default(self):
        """Define a default asset to the w_image component from w_reclass"""

        self.w_reclass.w_ic_select.v_model = str(param.LULC_DEFAULT)

        self.w_reclass.model.matrix = map_matrix_to_dict(param.LC_MAP_MATRIX)
