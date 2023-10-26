import ee
import pandas as pd
import pkg_resources
import sepal_ui.sepalwidgets as sw
from ipyleaflet import WidgetControl
from sepal_ui.mapping import SepalMap

import component.parameter.module_parameter as param
from component.tile.aoi_view import AoiView
from component.message import cm

__all__ = ["AoiTile"]

ee.Initialize()

{
    (2000, 2005): [2000, 2005],
    (2005, 2010): [2005, 2010],
    (2010, 2015): [2010, 2012, 2015],
    (2015, 2018): [2015, 2018],
    (2018, 2021): [2018, 2021],
}


class AoiTile(sw.Layout):
    """Custo AOI Tile"""

    def __init__(self):
        self.class_ = "d-block"
        self._metadata = {"mount_id": "aoi_tile"}

        super().__init__()

        self.map_ = SepalMap(gee=True)
        self.map_.dc.hide()
        self.map_.layout.height = "750px"
        self.map_.min_zoom = 2

        self.view = AoiView(
            map_=self.map_,
            methods=["-POINTS", "-DRAW"],
        )

        self.view.btn.children = [cm.aoi.view.btn]

        # Rename selection methos as referenced in:
        # https://github.com/dfguerrerom/sepal_mgci/issues/7
        self.view.w_method.items = param.CUSTOM_AOI_ITEMS
        self.view.w_admin_0.items = self.get_m49()

        aoi_control = WidgetControl(
            widget=self.view, position="topleft", transparent_bg=True
        )

        self.map_.add(aoi_control)

        self.children = [self.map_]

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
            item for item in self.view.w_admin_0.items if item["value"] in gaul_codes
        ]

        return m49_items
