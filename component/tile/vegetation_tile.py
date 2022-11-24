from pathlib import Path

import ipyvuetify as v
import sepal_ui.mapping as sm
import sepal_ui.sepalwidgets as sw
from ipywidgets import Layout
from sepal_ui.scripts.utils import loading_button
from traitlets import CBool, directional_link, link, observe

import component.parameter.directory as dir_
import component.parameter.module_parameter as param
import component.widget as cw
from component.message import cm

from . import reclassify_tile as rt

__all__ = ["VegetationTile", "Questionaire"]


class VegetationTile(v.Layout, sw.SepalWidget):
    def __init__(self, model, aoi_model, *args, **kwargs):

        self._metadata = {"mount_id": "vegetation_tile"}
        self.class_ = "d-block pa-2"

        super().__init__(*args, **kwargs)

        self.model = model
        self.aoi_model = aoi_model

        title = v.CardTitle(children=[cm.veg_layer.title])
        description = v.CardText(children=[sw.Markdown(cm.veg_layer.description)])

        w_questionaire = Questionaire()

        self.view = VegetationView(
            model=self.model,
            aoi_model=self.aoi_model,
            questionaire=w_questionaire,
        )

        cards = [
            [[w_questionaire], "Questionaire"],
            [[self.view], "Classification"],
        ]

        self.children = [v.Card(children=[title, description], class_="pa-2 mb-2")] + [
            v.Card(
                children=[v.CardTitle(children=[card[1]])] + card[0],
                class_="pa-2 mb-2",
            )
            for card in cards
        ]

        # Save the answer in the model. It will be used in the report
        directional_link((w_questionaire, "custom_lulc"), (self.model, "custom_lulc"))


class VegetationView(v.Layout, sw.SepalWidget):
    def __init__(self, model, aoi_model, questionaire, *args, **kwargs):

        self._metadata = {"mount_id": "vegetation_tile"}
        self.class_ = "d-block pa-2"
        # self.min_height = "400px"

        super().__init__(*args, **kwargs)

        self.model = model
        self.aoi_model = aoi_model
        self.w_questionaire = questionaire

        self.reclassify_tile = rt.ReclassifyTile(
            self.w_questionaire,
            results_dir=dir_.CLASS_DIR,
            save=False,
            aoi_model=self.aoi_model,
            default_class={
                "IPCC": str(param.LC_CLASSES),
            },
        )

        self.children = [self.reclassify_tile]

        directional_link((self.reclassify_tile.model, "matrix"), (self.model, "matrix"))
        directional_link(
            (self.reclassify_tile.model, "ic_items"), (self.model, "ic_items")
        )
        directional_link(
            (self.reclassify_tile.model, "dst_class"), (self.model, "lulc_classes")
        )

    def display_map(self, *args):
        """Display reclassified raster on map. Get the reclassify visualization
        image.

        .. deprecated:
            this is an orphan method. I will try to use later if requested
        """

        # Manually trigger the reclassify method
        self.reclassify_tile.w_reclass.reclassify(None, None, None)

        # Create a three band representation as this function was removed from the
        # reclassify tool
        reclass_model = self.reclassify_tile.w_reclass.model

        code, desc, color = zip(
            *[
                (str(k), str(v[0]), str(v[1]))
                for k, v in reclass_model.dst_class.items()
            ]
        )

        layer = reclass_model.dst_gee_memory.mask(self.model.kapos_image).visualize(
            **{
                "bands": reclass_model.band,
                "palette": color,
                "min": min(code),
                "max": max(code),
            }
        )

        # Create legend based on the lulc classes.
        self.map_.add_legend(
            legend_title="Legend", legend_dict=dict(self.model.lulc_classes.values())
        )
        # Do this trick to remove the scrolling bar in the legend output
        self.map_.legend_widget.layout = Layout(width="120px", overflow="none")

        # Remove previusly loaded layers
        [self.map_.remove_last_layer() for _ in range(len(self.map_.layers))]

        self.map_.zoom_ee_object(layer.geometry())
        self.map_.addLayer(layer)


class Questionaire(v.Layout, sw.SepalWidget):
    """Vegetation questionaire. Do some questions to the user, save the answers
    in the traits and use them later to display the proper Vegetation View

    """

    custom_lulc = CBool().tag(sync=True)

    def __init__(self, *args, **kwargs):

        self.class_ = "d-block"

        super().__init__(*args, **kwargs)

        self.w_custom_lulc = cw.BoolQuestion(cm.veg_layer.questionaire.q1)
        self.children = [self.w_custom_lulc]

        link((self.w_custom_lulc, "v_model"), (self, "custom_lulc"))
