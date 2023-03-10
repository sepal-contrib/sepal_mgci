from pathlib import Path

import pandas as pd
from sepal_ui import sepalwidgets as sw

import component.parameter.module_parameter as param
from component.reclassify.parameters import *
from component.widget import reclassify as rec

__all__ = ["ReclassifyTile"]


class ReclassifyTile(sw.Card):

    """Custom reclassify tile to replace the default Reclassify Tile and View
    from sepal_ui. This card will change depending on a input questionaire which
    aims to create a custom view depending on their answers."""

    def __init__(
        self,
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
        # I did this because in version 0 I didn't wanted to modify view.
        self.w_reclass.w_dst_class_file.select_file(default_class["IPCC"]).hide()
        self.w_reclass.model.dst_class_file = default_class["IPCC"]
        self.w_reclass.model.dst_class = self.w_reclass.model.get_classes()

        self.children = [self.w_reclass]

    def use_default(self):
        """Define a default asset to the w_image component from w_reclass"""

        self.w_reclass.model.matrix = dict(
            list(
                zip(
                    *list(
                        pd.read_csv(param.LC_MAP_MATRIX)[["from_code", "target_code"]]
                        .to_dict("list")
                        .values()
                    )
                )
            )
        )
