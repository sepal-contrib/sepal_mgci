from pathlib import Path

from traitlets import directional_link, observe, CBool, link
from ipywidgets import Layout

import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
import sepal_ui.mapping as sm
from sepal_ui.scripts.utils import loading_button

from component.message import cm
import component.widget as cw
import component.parameter as param
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
        self.map_ = sm.SepalMap()
        self.view = VegetationView(
            model=self.model,
            aoi_model=self.aoi_model,
            map_=self.map_,
            questionaire=w_questionaire,
        )

        cards = [
            [[w_questionaire], "Questionaire"],
            [[self.view], "Classification"],
            [[self.map_], "Visualize"],
        ]

        self.children = [v.Card(children=[title, description], class_="pa-2 mb-2")] + [
            v.Card(
                children=[v.CardTitle(children=[card[1]])] + card[0],
                class_="pa-2 mb-2",
            )
            for card in cards
        ]
        
        # Save the answer in the model. It will be used in the report
        directional_link((w_questionaire, 'custom_lulc'),(self.model, 'custom_lulc'))


class VegetationView(v.Layout, sw.SepalWidget):
    def __init__(self, model, aoi_model, map_, questionaire, *args, **kwargs):

        self._metadata = {"mount_id": "vegetation_tile"}
        self.class_ = "d-block pa-2"
        # self.min_height = "400px"

        super().__init__(*args, **kwargs)

        self.model = model
        self.aoi_model = aoi_model
        self.map_ = map_
        self.w_questionaire = questionaire

        self.reclassify_tile = rt.ReclassifyTile(
            self.w_questionaire,
            results_dir=param.CLASS_DIR,
            save=False,
            aoi_model=self.aoi_model,
            default_class={
                "IPCC": str(Path(__file__).parents[1] / "parameter/ipcc.csv"),
            },
        )

        self.display_btn = sw.Btn("Display on map", class_='mt-2')

        self.children = [self.reclassify_tile, self.display_btn]

        # Decorate functions
        self.display_map = loading_button(
            alert=sw.Alert(), button=self.display_btn, debug=True
        )(self.display_map)

        self.reclassify_tile.model.observe(self.update_model_vegetation, "remaped")

        # Let's bind the selected band with the model, it will be useful in the dashboard

        directional_link((self.reclassify_tile.model, "band"), (self.model, "year"))
        directional_link(
            (self.reclassify_tile.model, "dst_class"), (self.model, "lulc_classes")
        )

        self.display_btn.on_event("click", self.display_map)

    def update_mask(self, change):
        """Once the Kapos layer is created, update the reclassify mask to restrict
        the analysis to the mask"""

        self.reclassify_tile.model.mask = self.model.kapos_mask

    def update_model_vegetation(self, change):
        """Observe reclassify model, and update the mgci model. It will store
        the reclassified gee asset into the mgci model to perform operations.
        """
        if change["new"]:

            self.model.vegetation_image = (
                self.reclassify_tile.w_reclass.model.dst_gee_memory
            )

    def display_map(self, *args):
        """Display reclassified raster on map. Get the reclassify visualization
        image."""

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
    """
    Vegetation questionaire. Do some questions to the user, save the answers
    in the traits and use them later to display the proper Vegetation View

    """

    custom_lulc = CBool().tag(sync=True)
    class_file = CBool().tag(sync=True)

    def __init__(self, *args, **kwargs):

        self.class_ = "d-block"

        super().__init__(*args, **kwargs)

        self.w_custom_lulc = cw.BoolQuestion(cm.veg_layer.questionaire.q1)
        self.w_class_file = cw.BoolQuestion(cm.veg_layer.questionaire.q2).hide()

        self.children = [self.w_custom_lulc, self.w_class_file]

        link((self.w_custom_lulc, "v_model"), (self, "custom_lulc"))
        link((self.w_class_file, "v_model"), (self, "class_file"))

    @observe("custom_lulc")
    def toggle_question(self, change):
        """Toggle second question, based on the first answer"""

        if change["new"]:
            self.w_class_file.show()
        else:
            self.w_class_file.v_model = False
            self.w_class_file.hide()
