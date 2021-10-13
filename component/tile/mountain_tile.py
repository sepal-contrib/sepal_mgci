from ipywidgets import Layout
import ipyvuetify as v

import sepal_ui.mapping as sm
from sepal_ui.scripts.utils import loading_button
from sepal_ui import sepalwidgets as sw

from component.message import cm
import component.parameter as param
import component.widget as cw

__all__ = ["MountainTile"]


class MountainTile(v.Layout, sw.SepalWidget):
    def __init__(self, model, *args, **kwargs):

        self._metadata = {"mount_id": "mountain_tile"}
        self.class_ = "d-block pa-2"

        super().__init__(*args, **kwargs)

        self.model = model
        self.map_ = sm.SepalMap()
        self.view = MountainView(model=model, map_=self.map_)

        title = v.CardTitle(children=[cm.mountain_layer.title])
        description = v.CardText(children=[sw.Markdown(cm.mountain_layer.description)])

        self.children = [
            v.Card(class_="pa-2 mb-2", children=[title, description]),
            v.Card(class_="pa-2 mb-2", children=[self.view]),
            v.Card(
                class_="pa-2 mb-2",
                children=[v.CardTitle(children=["Visualize"]), self.map_],
            ),
        ]


class MountainView(v.Layout, sw.SepalWidget):
    def __init__(self, model, map_, *args, **kwargs):

        self.class_ = "d-block pa-2"

        super().__init__(*args, **kwargs)

        # Class parameters
        self.model = model
        self.map_ = map_

        # Widgets
        self.alert = sw.Alert()

        self.w_use_custom = v.RadioGroup(
            row=True,
            v_model=0,
            children=[
                v.Radio(label="No", value=0),
                v.Radio(label="Yes", value=1),
            ],
        )

        self.w_use_custom = cw.BoolQuestion(cm.mountain_layer.questionaire)

        self.w_custom_dem = sw.AssetSelect(
            label="Select a custom DEM", types=["IMAGE"]
        ).hide()

        self.btn = sw.Btn(cm.mountain_layer.btn, class_="mb-2")

        # bind the widgets to the model
        self.model.bind(self.w_use_custom, "use_custom")

        self.children = [self.alert, self.w_use_custom, self.w_custom_dem, self.btn]

        # actions
        self.w_use_custom.observe(self.display_custom_dem, "v_model")

        # Decorate functions
        self.add_kapos_map = loading_button(
            alert=self.alert, button=self.btn, debug=True
        )(self.add_kapos_map)

        self.btn.on_event("click", self.add_kapos_map)

    def display_custom_dem(self, change):
        """Display custom dem widget when w_select_dem == 'custom'"""

        v_model = change["new"]
        self.w_custom_dem.show() if v_model == 1 else self.w_custom_dem.hide()

    def add_kapos_map(self, widget, event, data):
        """Create and display kapos layer on a map"""

        self.model.get_kapos()

        # Create legend
        self.map_.add_legend(legend_title="Legend", legend_dict=param.KAPOS_LEGEND)
        # Do this trick to remove the scrolling bar in the legend output
        self.map_.legend_widget.layout = Layout(width="85px", overflow="none")

        # Add kapos mountain layer to map
        self.map_.zoom_ee_object(self.model.aoi_model.feature_collection.geometry())
        self.map_.addLayer(self.model.kapos_image, param.KAPOS_VIS, "Kapos map")

        # Create a trait to let others know that we have created a kapos layer
        self.model.kapos_done += 1
