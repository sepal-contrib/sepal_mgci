from typing import Tuple

import numpy as np
import pandas as pd

from ipecharts.option import Option, Legend, Tooltip
from ipecharts.option.series import Sankey
from ipecharts.echarts import EChartsWidget


def get_sankey_chart():

    sankey_data = Sankey(smooth=True, areaStyle={})
    sankey_data.nodes = []
    sankey_data.links = []
    option = Option(series=[sankey_data], tooltip=Tooltip(), legend=Legend())

    chart = EChartsWidget(option=option)

    return sankey_data, chart


def get_nodes_and_links(
    df: pd.DataFrame,
    lc_classes_path: str,
    years: Tuple[str, str] = ["from_lc", "to_lc"],
):
    """Generate nodes and links for a Sankey diagram"""

    from_lc, to_lc = [str(y) for y in years]

    # Load labels dictionary
    labels_df = pd.read_csv(lc_classes_path)

    # Generate a dictionary to map land cover classes to descriptions and colors
    desc_color_map = labels_df.set_index("lc_class")[["desc", "color"]].to_dict("index")

    # Dictionary to store nodes and links by biobelt
    biobelt_dict = {}

    # Group the dataframe by 'biobelt'
    grouped = df.groupby("belt_class")

    # Process each biobelt group separately
    for biobelt, group in grouped:
        # Identify unique land cover classes within the biobelt group
        unique_classes = np.unique(group[["from_lc", "to_lc"]].values)

        # Generate nodes with unique land cover classes and their corresponding colors
        nodes = []
        for lc_class in unique_classes:
            lc_info = desc_color_map.get(
                lc_class, {"desc": "Unknown", "color": "#000000"}
            )
            lc_label = lc_info["desc"]
            color = lc_info["color"]
            nodes.extend(
                {"name": f"{lc_label}_{year}", "itemStyle": {"color": color}}
                for year in [from_lc, to_lc]
            )

        # Generate links based on the biobelt group
        links = []
        for _, row in group.iterrows():
            source_info = desc_color_map.get(
                row["from_lc"], {"desc": "Unknown", "color": "#000000"}
            )
            target_info = desc_color_map.get(
                row["to_lc"], {"desc": "Unknown", "color": "#000000"}
            )
            links.append(
                {
                    "source": f"{source_info['desc']}_{from_lc}",
                    "target": f"{target_info['desc']}_{to_lc}",
                    "value": round(row["sum"], 2),  # Rounded to 2 decimal places
                }
            )

        # Store nodes and links for this biobelt in the dictionary
        biobelt_dict[biobelt] = {"nodes": nodes, "links": links}

    return biobelt_dict


def get_pyecharts_sankey(df: pd.DataFrame, lc_classes_path: str):
    """Generate a Sankey diagram using Pyecharts

    Args:
        df (pd.DataFrame): A DataFrame with columns 'from', 'to', and 'sum'
        lc_classes_path (str): Path to the land cover classes CSV file

    Returns:
        EChartsWidget: A Pyecharts EChartsWidget object
    """

    from ipecharts.option import Option, Legend, Tooltip
    from ipecharts.option.series import Sankey
    from ipecharts.echarts import EChartsWidget, EChartsRawWidget
    import numpy as np

    s = Sankey(smooth=True, areaStyle={})
    s.data = nodes
    s.links = links

    option = Option(series=[s], tooltip=Tooltip(), legend=Legend())
    return EChartsWidget(option=option)
