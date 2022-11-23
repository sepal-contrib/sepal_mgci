from datetime import datetime as dt

import sepal_ui.sepalwidgets as sw
from sepal_ui.aoi.aoi_model import AoiModel
from sepal_ui.aoi.aoi_view import AdminField, MethodSelect
from sepal_ui.message import ms
from sepal_ui.scripts import utils as su
from traitlets import Int

from component.scripts.biobelt import add_belt_map


class AoiView(sw.Layout):
    """Custom aoi view to display biobelt layer and lagend in the map as soon as the
    image"""

    # ##########################################################################
    # ###                             widget parameters                      ###
    # ##########################################################################

    updated = Int(0).tag(sync=True)
    "int: traitlets triggered every time a AOI is selected"

    ee = True
    "bool: either or not he aoi_view is connected to gee"

    folder = None
    "str: the folder name used in GEE related component, mainly used for debugging"

    model = None
    "sepal_ui.aoi.AoiModel: the model to create the AOI from the selected parameters"

    # ##########################################################################
    # ###                            the embeded widgets                     ###
    # ##########################################################################

    map_ = None
    "sepal_ui.mapping.SepalMap: the map to draw the AOI"

    w_method = None
    "widget: the widget to select the method"

    components = None
    "dict: the followingwidgets used to define AOI"

    w_admin_0 = None
    "widget: the widget used to select admin level 0"

    w_admin_1 = None
    "widget: the widget used to select admin level 1"

    w_admin_2 = None
    "widget: the widget used to select admin level 2"

    w_vector = None
    "widget: the widget used to select vector shapes"

    w_points = None
    "widget: the widget used to select points files"

    w_draw = None
    "widget: the widget used to select the name of a drawn shape (only if :code:`map_ != None`)"

    w_asset = None
    "widget: the widget used to select asset name of a featureCollection (only if :code:`gee == True`)"

    btn = None
    "sw.Btn: a default btn"

    alert = None
    "sw.Alert: a alert to display message to the end user"

    def __init__(
        self, methods="ALL", map_=None, gee=True, folder=None, model=None, **kwargs
    ):
        self.class_ = "d-block"

        # set ee dependencie
        self.ee = gee
        self.folder = folder

        gee is False or su.init_ee()

        # get the model
        self.model = model or AoiModel(gee=gee, folder=folder, **kwargs)

        # get the map if filled
        self.map_ = map_

        # create the method widget
        self.w_method = MethodSelect(methods, gee=gee, map_=map_)

        # add the methods blocks
        self.w_admin_0 = AdminField(0, gee=gee).get_items()
        self.w_admin_1 = AdminField(1, self.w_admin_0, gee=gee)
        self.w_admin_2 = AdminField(2, self.w_admin_1, gee=gee)
        self.w_vector = sw.VectorField(label=ms.aoi_sel.vector)
        self.w_points = sw.LoadTableField(label=ms.aoi_sel.points)
        self.w_draw = sw.TextField(label=ms.aoi_sel.aoi_name)

        # group them together with the same key as the select_method object
        self.components = {
            "ADMIN0": self.w_admin_0,
            "ADMIN1": self.w_admin_1,
            "ADMIN2": self.w_admin_2,
            "SHAPE": self.w_vector,
            "POINTS": self.w_points,
            "DRAW": self.w_draw,
        }

        # hide them all
        [c.hide() for c in self.components.values()]

        # use the same alert as in the model
        self.alert = sw.Alert()

        # bind the widgets to the model
        (
            self.model.bind(self.w_admin_0, "admin")
            .bind(self.w_admin_1, "admin")
            .bind(self.w_admin_2, "admin")
            .bind(self.w_vector, "vector_json")
            .bind(self.w_points, "point_json")
            .bind(self.w_method, "method")
            .bind(self.w_draw, "name")
        )

        # defint the asset select separately. If no gee is set up we don't want any
        # gee based widget to be requested. If it's the case, application that does
        # not support GEE
        # will crash if the user didn't authenticate
        if self.ee:
            self.w_asset = sw.VectorField(
                label=ms.aoi_sel.asset, gee=True, folder=self.folder, types=["TABLE"]
            ).hide()
            self.components["ASSET"] = self.w_asset
            self.model.bind(self.w_asset, "asset_name")

        # add a validation btn
        self.btn = sw.Btn(ms.aoi_sel.btn)

        # create the widget
        self.children = (
            [self.w_method] + [*self.components.values()] + [self.btn, self.alert]
        )

        super().__init__(**kwargs)

        # js events
        self.w_method.observe(self._activate, "v_model")  # activate widgets
        self.btn.on_event("click", self._update_aoi)  # load the informations

        # reset te aoi_model
        self.model.clear_attributes()

    @su.loading_button(debug=True)
    def _update_aoi(self, widget, event, data):
        """load the object in the model & update the map (if possible)"""

        # read the information from the geojson datas
        if self.map_:
            self.map_.remove_all()
            self.model.geo_json = self.map_.dc.to_json()

        if hasattr(self.map_, "legend"):
            self.map_.legend.legend_dict = {}

        # update the model
        self.model.set_object()

        # update the map
        if self.map_:
            self.map_.remove_layer("aoi", none_ok=True)
            self.map_.zoom_bounds(self.model.total_bounds())

            if self.ee:
                self.map_.add_ee_layer(self.model.feature_collection, {}, name="aoi")
            else:
                self.map_.add_layer(self.model.get_ipygeojson())

            self.map_.hide_dc()

        add_belt_map(self.model, self.map_)

        # tell the rest of the apps that the aoi have been updated
        self.updated += 1

        self.alert.add_msg(ms.aoi_sel.complete, "success")

        return self

    def reset(self):
        """clear the aoi_model from input and remove the layer from the map (if existing)"""

        # reset the view of the widgets
        self.w_method.v_model = None

        # clear the map
        self.map_ is None or self.map_.remove_layer("aoi", none_ok=True)

        return self

    @su.switch("loading", on_widgets=["w_method"])
    def _activate(self, change):
        """activate the adapted widgets"""

        # clear and hide the alert
        self.alert.reset()

        # hide the widget so that the user doens't see status changes
        [w.hide() for w in self.components.values()]

        # clear the inputs in a second step as reseting a FileInput can be long
        [w.reset() for w in self.components.values()]

        # deactivate or activate the dc
        # clear the geo_json saved features to start from scratch
        if self.map_:
            if change["new"] == "DRAW":
                self.map_.dc.show()
            else:
                self.map_.dc.hide()

        # activate the correct widget
        w = next((w for k, w in self.components.items() if k == change["new"]), None)
        w is None or w.show()

        # init the name to the current value
        now = dt.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.w_draw.v_model = None if change["new"] is None else f"Manual_aoi_{now}"

        return
