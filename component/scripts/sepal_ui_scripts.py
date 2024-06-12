"""Scripts that required components from the sepal_ui module."""

import pandas as pd
import component.parameter.module_parameter as param

from sepal_ui.aoi.aoi_model import AoiModel
from typing import Tuple


def get_geoarea(aoi_model: AoiModel) -> Tuple[str, str]:
    """Create the geo area name to the excel report"""

    if aoi_model.method in ["ADMIN0", "ADMIN1", "ADMIN2"]:
        split_name = aoi_model.name.split("_")

        iso31661 = split_name[0]

        m49_df = pd.read_csv(param.M49_FILE, sep=";")

        gaul_row = m49_df[m49_df.iso31661 == iso31661]

        geoarea_name = gaul_row["country"].values[0]
        m49_code = gaul_row["m49"].values[0]

        if len(split_name) > 1:
            geoarea_name = f"{geoarea_name}_" + "_".join(split_name[1:])
        return geoarea_name, m49_code
    else:
        return aoi_model.name, ""
