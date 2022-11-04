import ee

ee.Initialize()

import pandas as pd
import sepal_ui.sepalwidgets as sw
from sepal_ui.mapping import SepalMap

import component.parameter as param
from component.tile.aoi_view import AoiView
from component.widget.legend_control import LegendControl

__all__ = ["AoiTile"]


class AoiTile(sw.Layout):
    """Custo AOI Tile"""

    def __init__(self, methods="ALL", gee=True):

        super().__init__()

        # create the map
        self.map_ = SepalMap(dc=True, gee=gee)
        self.map_.dc.hide()

        self.view = AoiView(
            map_=self.map_,
            methods=["-POINTS", "-DRAW"],
        )

        # Rename selection methos as referenced in:
        # https://github.com/dfguerrerom/sepal_mgci/issues/7
        self.view.w_method.items = param.CUSTOM_AOI_ITEMS
        self.view.w_admin_0.items = self.get_m49()

        self.children = [
            sw.Flex(xs12=True, md5=True, class_="pa-5", children=[self.view]),
            sw.Flex(xs12=True, md7=True, class_="pa-1", children=[self.map_]),
        ]

    def get_m49(self):
        """Display only the countries that matches with m49"""

        # Read m49 countries.
        m49_countries = pd.read_csv(param.M49_FILE, sep=";")

        # Read AOI gaul dataframe
        gaul_dataset = (
            pd.read_csv(self.view.model.FILE[1])
            .drop_duplicates(subset=self.view.model.CODE[1].format(0))
            .sort_values(self.view.model.NAME[1].format(0))
            .rename(columns={"ISO 3166-1 alpha-3": "iso31661"})
        )

        # Get only the gaul contries present in the m49
        m49_dataset = gaul_dataset[gaul_dataset.iso31661.isin(m49_countries.iso31661)]
        gaul_codes = m49_dataset.ADM0_CODE.to_list()

        # Subset new items
        m49_items = [
            item for item in self.view.w_admin_0.items if item["value"] in gaul_codes
        ]

        return m49_items
