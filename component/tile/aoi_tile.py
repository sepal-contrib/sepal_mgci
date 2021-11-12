from sepal_ui import aoi
import pandas as pd

import component.parameter as param

__all__ = ["aoi_tile"]

# Define area of interest tile
aoi_tile = aoi.AoiTile(methods=["-POINTS", "-DRAW"])

# Rename selection methos as referenced in:
# https://github.com/dfguerrerom/sepal_mgci/issues/7

aoi_tile.view.w_method.items = param.CUSTOM_AOI_ITEMS
aoi_view = aoi_tile.view
aoi_model = aoi_view.model

# Display only the countries that matches with m49

# Read m49 countries.
m49_countries = pd.read_csv(param.M49_FILE, sep=";")

# Read AOI gaul dataframe
gaul_dataset = (
    pd.read_csv(aoi_model.FILE[1])
    .drop_duplicates(subset=aoi_model.CODE[1].format(0))
    .sort_values(aoi_model.NAME[1].format(0))
    .rename(columns={"ISO 3166-1 alpha-3": "iso31661"})
)

# Get only the gaul contries present in the m49
m49_dataset = gaul_dataset[gaul_dataset.iso31661.isin(m49_countries.iso31661)]
gaul_codes = m49_dataset.ADM0_CODE.to_list()

# Create the new items
m49_items = [item for item in aoi_view.w_admin_0.items if item["value"] in gaul_codes]

# Replace them.
aoi_view.w_admin_0.items = m49_items
