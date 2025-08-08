import asyncio
import pkg_resources
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
from sepal_ui.aoi.aoi_view import AdminField
import sepal_ui.sepalwidgets as sw
from sepal_ui import mapping as sm
from sepal_ui.scripts.gee_task import GEETask


from component.widget.legend_control import LegendControl
from component.scripts.biobelt import get_belt_area
from component.parameter.module_parameter import BIOBELT, BIOBELT_LEGEND, BIOBELT_VIS
from component.widget.legend_control import LegendControl
from component.message import cm
import component.parameter.module_parameter as param
import logging

log = logging.getLogger("MGCI.aoi_tile")


class AoiView(AoiView, sw.Card):
    """Custom AOI view to add the biobelt map after the AOI selection."""

    def __init__(self, map_: sm.SepalMap, **kwargs: dict):
        self.map_ = map_
        self.class_ = "elevation-0"

        if self.map_:  # for debugging
            self.map_.legend = LegendControl({}, title="", position="bottomright")
            self.map_.add_control(self.map_.legend)
        log.debug("About to initialize AoiView with map_")
        super().__init__(
            map_=self.map_, gee_interface=self.map_.gee_interface, **kwargs
        )
        log.debug("AoiView initialized")

        self.btn.children = [cm.aoi.view.btn]
        self.btn.small = True
        self.w_method.items = param.CUSTOM_AOI_ITEMS
        self.w_admin_0.items = self.get_m49()

        self._tasks: dict[str, GEETask] = {}

        self.configure_tasks()

    def get_m49(self):
        """Display only the countries that matches with m49"""

        # Read m49 countries.
        m49_countries = pd.read_csv(param.M49_FILE, sep=";")

        # Access to the parquet file in the package data (required with sepal_ui>2.16.4)
        resource_path = "data/gaul_database.parquet"
        content = pkg_resources.resource_filename("pygaul", resource_path)

        df = pd.read_parquet(content).astype(str)

        # Read AOI gaul dataframe
        gaul_dataset = (
            df.drop_duplicates(subset="ADM{}_CODE".format(0))
            .sort_values("ADM{}_NAME".format(0))
            .rename(columns={"ISO 3166-1 alpha-3": "iso31661"})
        )

        # Get only the gaul contries present in the m49
        m49_dataset = gaul_dataset[gaul_dataset.iso31661.isin(m49_countries.iso31661)]
        gaul_codes = m49_dataset.ADM0_CODE.astype(str).to_list()

        # Remove countries that are not present in gaul_dataset
        m49_items = [
            item for item in self.w_admin_0.items if item["value"] in gaul_codes
        ]

        return m49_items

    async def add_aoi(self):
        """Get map_id of aoi and bounds"""

        coros = [
            self.map_.gee_interface.get_info_async(
                self.model.feature_collection.geometry().bounds().coordinates().get(0)
            ),
            self.map_.add_ee_layer_async(self.model.feature_collection, name="AOI"),
        ]

        coords, _ = await asyncio.gather(*coros)

        self.map_.zoom_bounds((*coords[0], *coords[2]))

        # tell the rest of the apps that the aoi have been updated
        self.updated += 1

    async def get_belt_map(self):

        self.map_.legend.loading = True

        biobelt_layer = self.map_.add_ee_layer_async(
            ee.Image(BIOBELT).clip(
                self.model.feature_collection.geometry().simplify(1000)
            ),
            name=cm.aoi.legend.belts,
            vis_params=BIOBELT_VIS,
        )

        belt_area = get_belt_area(
            self.model.feature_collection.geometry(), ee.Image(BIOBELT)
        )

        coros = [biobelt_layer, belt_area]

        try:
            biobelt_layer, belt_area = await asyncio.gather(*coros)
            legend_dict, _ = belt_area

            self.map_.legend.legend_dict = {}
            self.map_.legend.legend_dict = deepcopy(legend_dict)

            self.alert.add_msg(ms.aoi_sel.complete, "success")

        except Exception as e:
            self.map_.legend.set_error(f"Failed to get biobelt map: {e}")
        finally:
            self.map_.legend.loading = False

    def configure_tasks(self):
        """Configure the tasks to be used in the AOI view."""

        def after_select_aoi(*_):
            """Callback to add the AOI to the map after the selection."""
            self.btn.loading = False

            # TODO: here I can close the dialog and move to next step

        def get_belt_map(*_):
            """Callback to get the biobelt map after the AOI is added."""
            self._tasks["get_belt_map"].start()

        self._tasks["add_aoi"] = self.map_.gee_interface.create_task(
            func=self.add_aoi,
            key="add_aoi",
            on_error=lambda x: None,
            on_done=get_belt_map,
        )

        self._tasks["get_belt_map"] = self.map_.gee_interface.create_task(
            func=self.get_belt_map,
            key="get_belt_map",
            on_error=lambda x: None,
            on_finally=after_select_aoi,
        )

    def _update_aoi(self, *args) -> Self:
        """load the object in the model & update the map (if possible)."""

        try:
            self.btn.loading = True
            self.alert.reset()

            # read the information from the geojson datas
            if self.map_:
                self.map_.remove_all()
                self.map_.legend.hide()
                self.model.geo_json = self.aoi_dc.to_json()
                self.aoi_dc.hide()

            # update the model
            self.model.set_object()

            self._tasks["add_aoi"].start()
        except Exception as e:
            log.error(f"Failed to update AOI: {e}", exc_info=True)
            self.alert.add_msg(f"Failed to update AOI: {e}", "error")
        finally:
            self.btn.loading = False


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
            properties = self.map_.gee_interface.get_info(
                feature.toDictionary(feature.propertyNames())
            )

        iso = str(properties.get("iso3_code"))
        names = [value for prop, value in properties.items() if "name" in prop]

        # generate the name from the columns
        names = [su.normalize_str(name) for name in names]
        names[0] = iso

        self.name = "_".join(names)
