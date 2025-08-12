from pathlib import Path

from traitlets import directional_link

from sepal_ui import sepalwidgets as sw
from sepal_ui.scripts.sepal_client import SepalClient

from component.model.model import MgciModel
import component.parameter.module_parameter as param
from component.parameter.directory import dir_
from component.widget import reclassify as rec
from component.message import cm
from component.scripts.scripts import map_matrix_to_dict


__all__ = ["ReclassifyTile"]
import logging

log = logging.getLogger("MGCI.reclassify_tile")


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
        default_asset: list = [],
        sepal_client: SepalClient = None,
        *args,
        **kwargs,
    ):
        """

        Args:

            default_asset: list, default asset to pass to the w_reclass component


        """
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
            dst_class_file=str(dir_.class_dir / "default_lc_classification.csv"),
        )

        # set the tabs elements
        self.w_reclass = rec.ReclassifyView(
            self.model,
            out_path=dir_.matrix_dir,
            gee=gee,
            default_class=default_class,
            aoi_model=aoi_model,
            folder=folder,
            enforce_aoi=True,
            id_=id_,
            alert=alert,
            sepal_client=sepal_client,
            default_asset=default_asset,
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

    def use_default(self):
        """Define a default asset to the w_image component from w_reclass"""

        # self.w_reclass.w_ic_select.v_model = str(param.LULC_DEFAULT)
        log.debug("Setting default asset in w_reclass")
        self.w_reclass.w_ic_select.default_asset = [str(param.LULC_DEFAULT)]
        self.w_reclass.w_ic_select.v_model = str(param.LULC_DEFAULT)
        log.debug(
            "default asset set {}".format(self.w_reclass.w_ic_select.default_asset)
        )

        self.use_default_matrix()

    def use_default_matrix(self):
        """Define a default matrix to the w_reclass component"""

        log.debug("Setting default matrix in w_reclass")
        self.w_reclass.model.matrix = map_matrix_to_dict(param.LC_MAP_MATRIX)

    def use_empty_matrix(self):
        """Define an empty matrix to the w_reclass component"""

        log.debug("Setting empty matrix in w_reclass")
        self.w_reclass.model.matrix = {}
