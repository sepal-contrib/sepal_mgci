from datetime import datetime as dt
from pathlib import Path
from typing import Dict, List, Optional, Union

import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
import traitlets as t
from sepal_ui import mapping as sm
from sepal_ui.aoi.aoi_model import AoiModel
from sepal_ui.aoi.aoi_view import AdminField, MethodSelect
from component.message import cm
from sepal_ui.scripts import decorator as sd
from sepal_ui.scripts import utils as su
from typing_extensions import Self

from component.scripts.biobelt import add_belt_map


class AoiView(sw.Card):
    # ##########################################################################
    # ###                             widget parameters                      ###
    # ##########################################################################

    updated: t.Int = t.Int(0).tag(sync=True)
    "Traitlets triggered every time a AOI is selected"

    gee: bool = True
    "Either or not he aoi_view is connected to gee"

    folder: Union[str, Path] = ""
    "The folder name used in GEE related component, mainly used for debugging"

    model: Optional[AoiModel] = None
    "The model to create the AOI from the selected parameters"

    map_style: Optional[dict] = None
    "The predifined style of the aoi on the map"

    # ##########################################################################
    # ###                            the embeded widgets                     ###
    # ##########################################################################

    map_: Optional[sm.SepalMap] = None
    "The map to draw the AOI"

    aoi_dc: Optional[sm.DrawControl] = None
    "the drawing control associated with DRAW method"

    w_method: Optional[MethodSelect] = None
    "The widget to select the method"

    components: Dict[str, v.VuetifyWidget] = {}
    "The followingwidgets used to define AOI"

    w_admin_0: Optional[AdminField] = None
    "The widget used to select admin level 0"

    w_admin_1: Optional[AdminField] = None
    "The widget used to select admin level 1"

    w_admin_2: Optional[AdminField] = None
    "The widget used to select admin level 2"

    w_vector: Optional[sw.VectorField] = None
    "The widget used to select vector shapes"

    w_points: Optional[sw.LoadTableField] = None
    "The widget used to select points files"

    w_draw: Optional[sw.TextField] = None
    "The widget used to select the name of a drawn shape (only if :code:`map_ != None`)"

    w_asset: Optional[sw.AssetSelect] = None
    "The widget used to select asset name of a featureCollection (only if :code:`gee == True`)"

    btn: Optional[sw.Btn] = None
    "A default btn"

    alert: Optional[sw.Alert] = None
    "A alert to display message to the end user"

    def __init__(
        self,
        methods: Union[str, List[str]] = "ALL",
        map_: Optional[sm.SepalMap] = None,
        gee: bool = True,
        folder: Union[str, Path] = "",
        model: Optional[AoiModel] = None,
        map_style: Optional[dict] = None,
        **kwargs,
    ) -> None:
        r"""
        Versatile card object to deal with the aoi selection. multiple selection method are available (see the MethodSelector object) and the widget can be fully customizable. Can also be bound to ee (ee==True) or not (ee==False).

        Args:
            methods: the methods to use in the widget, default to 'ALL'. Available: {'ADMIN0', 'ADMIN1', 'ADMIN2', 'SHAPE', 'DRAW', 'POINTS', 'ASSET', 'ALL'}
            map\_: link the aoi_view to a custom SepalMap to display the output, default to None
            gee: wether to bind to ee or not
            vector: the path to the default vector object
            admin: the administrative code of the default selection. Need to be GADM if :code:`ee==False` and GAUL 2015 if :code:`ee==True`.
            asset: the default asset. Can only work if :code:`ee==True`
            map_style: the predifined style of the aoi. It's by default using a "success" ``sepal_ui.color`` with 0.5 transparent fill color. It can be completly replace by a fully qualified `style dictionnary <https://ipyleaflet.readthedocs.io/en/latest/layers/geo_json.html>`__. Use the ``sepal_ui.color`` object to define any color to remain compatible with light and dark theme.
        """
        self.class_ = "d-block pa-2 py-4"
        self.min_width = "462px"
        self.max_width = "462px"

        # set ee dependencie
        self.gee = gee
        self.folder = folder
        if gee is True:
            su.init_ee()

        # get the model
        self.model = model or AoiModel(gee=gee, folder=folder, **kwargs)

        # get the map if filled
        self.map_ = map_

        # get the aoi geoJSON style
        self.map_style = map_style

        # create the method widget
        self.w_method = MethodSelect(methods, gee=gee, map_=map_)

        # add the methods blocks
        self.w_admin_0 = AdminField(0, gee=gee).get_items()
        self.w_admin_1 = AdminField(1, self.w_admin_0, gee=gee)
        self.w_admin_2 = AdminField(2, self.w_admin_1, gee=gee)
        self.w_vector = sw.VectorField(label=ms.aoi_sel.vector)
        self.w_points = sw.LoadTableField(label=ms.aoi_sel.points)

        # group them together with the same key as the select_method object
        self.components = {
            "ADMIN0": self.w_admin_0,
            "ADMIN1": self.w_admin_1,
            "ADMIN2": self.w_admin_2,
            "SHAPE": self.w_vector,
            "POINTS": self.w_points,
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
        )

        # defint the asset select separately. If no gee is set up we don't want any
        # gee based widget to be requested. If it's the case, application that does not support GEE
        # will crash if the user didn't authenticate
        if self.gee:
            self.w_asset = sw.VectorField(
                label=ms.aoi_sel.asset, gee=True, folder="", types=["TABLE"]
            )
            self.w_asset.hide()
            self.components["ASSET"] = self.w_asset
            self.model.bind(self.w_asset, "asset_json")

        # define DRAW option separately as it will only work if the map is set
        if self.map_:
            self.w_draw = sw.TextField(label=ms.aoi_sel.aoi_name).hide()
            self.components["DRAW"] = self.w_draw
            self.model.bind(self.w_draw, "name")
            self.aoi_dc = sm.DrawControl(self.map_)
            self.aoi_dc.hide()

        # add a validation btn
        self.btn = sw.Btn(msg=ms.aoi_sel.btn)

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

    @sd.loading_button(debug=True)
    def _update_aoi(self, *args) -> Self:
        """load the object in the model & update the map (if possible)."""
        # read the information from the geojson datas
        if self.map_:
            self.model.geo_json = self.aoi_dc.to_json()

        # update the model
        self.model.set_object()
        self.alert.add_msg(ms.aoi_sel.complete, "success")

        # update the map
        if self.map_:
            self.map_.remove_layer("aoi", none_ok=True)
            self.map_.zoom_bounds(self.model.total_bounds())
            self.map_.add_layer(self.model.get_ipygeojson(self.map_style))

            self.aoi_dc.hide()

        add_belt_map(self.model, self.map_)

        # tell the rest of the apps that the aoi have been updated
        self.updated += 1

        return self

    def reset(self) -> Self:
        """clear the aoi_model from input and remove the layer from the map (if existing)."""
        # reset the view of the widgets
        self.w_method.v_model = None

        # clear the map
        if self.map_ is not None:
            self.map_.remove_layer("aoi", none_ok=True)

        return self

    @sd.switch("loading", on_widgets=["w_method"])
    def _activate(self, change: dict) -> None:
        """activate the adapted widgets."""
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
                self.aoi_dc.show()
            else:
                self.aoi_dc.hide()

        # activate the correct widget
        w = next((w for k, w in self.components.items() if k == change["new"]), None)
        w is None or w.show()

        # init the name to the current value
        now = dt.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.w_draw.v_model = None if change["new"] is None else f"Manual_aoi_{now}"

        return
