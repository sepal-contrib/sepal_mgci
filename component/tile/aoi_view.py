import json
import traitlets as t
from typing_extensions import Self
from copy import deepcopy

import ee
import pygaul
import pandas as pd

from sepal_ui.aoi.aoi_model import AoiModel
from sepal_ui.aoi.aoi_view import AoiView
from sepal_ui.message import ms
from sepal_ui.scripts import decorator as sd
from sepal_ui.scripts import utils as su
from sepal_ui.aoi.aoi_view import AdminField, MethodSelect
import sepal_ui.sepalwidgets as sw
from sepal_ui import mapping as sm

from component.widget.legend_control import LegendControl
from component.scripts.biobelt import get_belt_area
from component.parameter.module_parameter import BIOBELT, BIOBELT_LEGEND, BIOBELT_VIS
from component.scripts.thread_controller import TaskController
from component.widget.legend_control import LegendControl
from component.message import cm


class AdminField(AdminField):
    """Abstract class to load the admin data from the GAUL 2024 dataset"""

    df = pd.read_csv("component/parameter/gaul_2024_database.csv")

    def load_data(self, level, parent_code=None):
        """Generic method to load admin data by level

        Args:
            level: Admin level (0=country, 1=state, 2=district)
            parent_code: Code of the parent admin unit

        Returns:
            List of dictionaries with admin units data
        """
        if level == 0:
            cols = ["gaul0_name", "gaul0_code"]
            filter_condition = None
        elif level == 1:
            cols = ["gaul1_name", "gaul1_code"]
            filter_condition = self.df["gaul0_code"] == int(parent_code)
        elif level == 2:
            cols = ["gaul2_name", "gaul2_code"]
            filter_condition = self.df["gaul1_code"] == int(parent_code)
        else:
            return []

        filtered_df = (
            self.df[filter_condition] if filter_condition is not None else self.df
        )

        return (
            filtered_df[cols]
            .drop_duplicates()
            .rename(columns={f"gaul{level}_name": "text", f"gaul{level}_code": "value"})
            .sort_values(by="text")
            .astype({"value": str})  # to mantain the same format as in the past
            .to_dict(orient="records")
        )

    def get_items(self, filter_: str = "") -> Self:

        self.items = self.load_data(self.level, filter_)
        return self


class AoiModel(AoiModel):
    """Custom AOI model to use simplified GAUL 2024 dataset"""

    df = pd.read_csv("component/parameter/gaul_2024_database.csv")

    def _from_admin(self, admin: str) -> Self:
        """Get the feature collection from the admin code."""

        feature_collection = ee.FeatureCollection(
            {
                "ADMIN0": "projects/ee-andyarnellgee/assets/crosscutting/GAUL_2024_L0_simplify_0_001deg_dice10k",
                "ADMIN1": "projects/sat-io/open-datasets/FAO/GAUL/GAUL_2024_L1",
                "ADMIN2": "projects/sat-io/open-datasets/FAO/GAUL/GAUL_2024_L2",
            }[self.method]
        )

        if self.method == "ADMIN0":
            country_df = self.df[self.df.gaul0_code == int(admin)][
                ["iso3_code", "gaul0_code", "gaul0_name"]
            ]

            iso_code = country_df.reset_index().iloc[0, 1]
            self.feature_collection = feature_collection.filter(
                ee.Filter.eq("iso3_code", iso_code)
            )

            properties = country_df.reset_index().iloc[0, 1:].to_dict()

        else:
            code = ["gaul1_code", "gaul2_code"][int(self.method == "ADMIN2")]
            self.feature_collection = feature_collection.filter(
                ee.Filter.eq(code, int(admin))
            )

            # get the ADM0_CODE to get the ISO code
            feature = self.feature_collection.first()
            properties = self.gee_interface.get_info(
                feature.toDictionary(feature.propertyNames())
            )

        iso = str(properties.get("iso3_code"))
        names = [value for prop, value in properties.items() if "name" in prop]

        # generate the name from the columns
        names = [su.normalize_str(name) for name in names]
        names[0] = iso

        self.name = "_".join(names)


class AoiView(AoiView, sw.Card):
    """Custom AOI view to add the biobelt map after the AOI selection."""

    def __init__(self, map_, **kwargs: dict):

        methods = ["-POINTS", "-DRAW"]
        model = AoiModel()

        card_kwargs = {
            "class_": "d-block pa-2 py-4",
            "min_width": "462px",
            "max_width": "462px",
        }
        sw.Card.__init__(self, **card_kwargs)

        # >>>>> from here on, I it is just a copy of the AoiView init method

        gee = True
        folder = ""
        gee_session = None
        map_style = None

        # set ee dependency
        self.gee = gee
        self.folder = folder
        if gee is True:
            su.init_ee()

        # get the model
        self.model = model or AoiModel(
            gee=gee, folder=folder, gee_session=gee_session, **kwargs
        )

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
        self.w_vector = sw.VectorField(label=ms.aoi_sel.vector, gee_session=gee_session)
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

        # define the asset select separately. If no gee is set up we don't want any
        # gee based widget to be requested. If it's the case, application that does not support GEE
        # will crash if the user didn't authenticate
        if self.gee:
            self.w_asset = sw.VectorField(
                label=ms.aoi_sel.asset,
                gee=True,
                folder=self.folder,
                types=["TABLE"],
                gee_session=gee_session,
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

        # js events
        self.w_method.observe(self._activate, "v_model")  # activate widgets
        self.btn.on_event("click", self._update_aoi)  # load the information

        # reset the aoi_model
        self.model.clear_attributes()

        # >>>>> Up to here!!!

        # Define as class member so it can be accessed from outside.
        if self.map_:  # for debugging
            self.map_.legend = LegendControl({}, title="", position="bottomright")
            self.map_.add_control(self.map_.legend)

    @sd.loading_button()
    def _update_aoi(self, *args) -> Self:
        """load the object in the model & update the map (if possible)."""
        # read the information from the geojson datas
        if self.map_:
            self.map_.remove_all()
            self.map_.legend.hide()
            self.model.geo_json = self.aoi_dc.to_json()

        # update the model
        self.model.set_object()

        # update the map
        if self.map_:
            self.map_.zoom_bounds(self.model.total_bounds())
            self.map_.add_ee_layer(self.model.feature_collection)
            self.aoi_dc.hide()
            self.add_belt_map(self.model, self.map_)

        self.alert.add_msg(ms.aoi_sel.complete, "success")

        # tell the rest of the apps that the aoi have been updated
        self.updated += 1

        return self

    def add_belt_map(self, aoi_model, map_):
        """Create and display bioclimatic belt layer on a map."""

        def _update_legend(result):
            """Update the legend with the biobelt map data."""
            try:
                legend_dict, _ = result
                legend.legend_dict = {}
                legend.legend_dict = deepcopy(legend_dict)
            except Exception as e:
                legend.set_error(f"Failed to update legend: {e}")

            finally:
                legend.loading = False

        try:
            map_.zoom = 4

            aoi = aoi_model.feature_collection.geometry()
            map_.zoom_ee_object(aoi.bounds())

            biobelt = ee.Image(BIOBELT).clip(aoi.simplify(1000))
            map_.addLayer(biobelt, BIOBELT_VIS, cm.aoi.legend.belts)

        except Exception as e:

            raise Exception(f"Failed to add biobelt map: {e}")

        finally:

            try:

                legend = map_.legend
                legend.loading = True

                task_controller = TaskController(
                    function=get_belt_area,
                    aoi=aoi,
                    biobelt=biobelt,
                    callback=_update_legend,
                    disable_components=[self],
                )

                task_controller.start_task()

            except Exception as e:

                legend.set_error(f"Failed to update legend: {e}")

            finally:

                legend.loading = False
