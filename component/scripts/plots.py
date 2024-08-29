from typing import Tuple
from component.parameter.module_parameter import transition_degradation_matrix
from collections import defaultdict

import matplotlib.pyplot as plt
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


def sankey(df, colorDict=None, aspect=4, rightColor=False, fontsize=14):
    """
    Sankey Diagram for showing land cover transitions
    Inputs:
        df = pandas dataframe with first column as left, second column as right and third colum as leftWeight
        colorDict = Dictionary of colors to use for each label
            {'label':'color'}
        aspect = vertical extent of the diagram in units of horizontal extent
        rightColor = If true, each strip in the diagram will be be colored
                    according to its left label
    Ouput: fig, ax
    """
    left = df[df.columns[0]]
    right = df[df.columns[1]]
    leftWeight = df["sum"]
    rightWeight = []

    leftLabels = []
    rightLabels = []
    # Check weights
    if len(leftWeight) == 0:
        leftWeight = np.ones(len(left))

    if len(rightWeight) == 0:
        rightWeight = leftWeight

    fig, ax = plt.subplots(figsize=(4, 6))

    # Create Dataframe
    if isinstance(left, pd.Series):
        left = left.reset_index(drop=True)
    if isinstance(right, pd.Series):
        right = right.reset_index(drop=True)
    dataFrame = pd.DataFrame(
        {
            "left": left,
            "right": right,
            "leftWeight": leftWeight,
            "rightWeight": rightWeight,
        },
        index=range(len(left)),
    )

    if len(dataFrame[(dataFrame.left.isnull()) | (dataFrame.right.isnull())]):
        raise ValueError("Sankey graph does not support null values.")

    # Identify all labels that appear 'left' or 'right'

    # Identify left labels
    if len(leftLabels) == 0:
        leftLabels = pd.Series(dataFrame.left.unique()).unique()

    # Identify right labels
    if len(rightLabels) == 0:
        rightLabels = pd.Series(dataFrame.right.unique()).unique()

    # If no colorDict given
    if colorDict is None:
        raise ValueError("specify a colour palette")

    # Determine widths of individual strips
    ns_l = defaultdict()
    ns_r = defaultdict()
    for leftLabel in leftLabels:
        leftDict = {}
        rightDict = {}
        for rightLabel in rightLabels:
            leftDict[rightLabel] = dataFrame[
                (dataFrame.left == leftLabel) & (dataFrame.right == rightLabel)
            ].leftWeight.sum()
            rightDict[rightLabel] = dataFrame[
                (dataFrame.left == leftLabel) & (dataFrame.right == rightLabel)
            ].rightWeight.sum()
        ns_l[leftLabel] = leftDict
        ns_r[leftLabel] = rightDict

    # Determine positions of left label patches and total widths
    leftWidths = defaultdict()
    for i, leftLabel in enumerate(leftLabels):
        myD = {}
        myD["left"] = dataFrame[dataFrame.left == leftLabel].leftWeight.sum()
        if i == 0:
            myD["bottom"] = 0
            myD["top"] = myD["left"]
            topEdge = myD["top"]
        else:
            myD["bottom"] = (
                leftWidths[leftLabels[i - 1]]["top"] + 0.02 * dataFrame.leftWeight.sum()
            )
            myD["top"] = myD["bottom"] + myD["left"]
            topEdge = myD["top"]
        leftWidths[leftLabel] = myD

    # Determine positions of right label patches and total widths
    rightWidths = defaultdict()
    for i, rightLabel in enumerate(rightLabels):
        myD = {}
        myD["right"] = dataFrame[dataFrame.right == rightLabel].rightWeight.sum()
        if i == 0:
            myD["bottom"] = 0
            myD["top"] = myD["right"]
            topEdge = myD["top"]
        else:
            myD["bottom"] = (
                rightWidths[rightLabels[i - 1]]["top"]
                + 0.02 * dataFrame.rightWeight.sum()
            )
            myD["top"] = myD["bottom"] + myD["right"]
            topEdge = myD["top"]
        rightWidths[rightLabel] = myD

    # Total vertical extent of diagram
    xMax = topEdge / aspect

    # Draw vertical bars on left and right of each  label's section & print label
    for leftLabel in leftLabels:
        ax.fill_between(
            [-0.02 * xMax, 0],
            2 * [leftWidths[leftLabel]["bottom"]],
            2 * [leftWidths[leftLabel]["bottom"] + leftWidths[leftLabel]["left"]],
            color=colorDict[leftLabel],
            alpha=0.99,
        )
        ax.text(
            -0.05 * xMax,
            leftWidths[leftLabel]["bottom"] + 0.5 * leftWidths[leftLabel]["left"],
            leftLabel,
            {"ha": "right", "va": "center"},
            fontsize=fontsize,
        )
    for rightLabel in rightLabels:
        ax.fill_between(
            [xMax, 1.02 * xMax],
            2 * [rightWidths[rightLabel]["bottom"]],
            2 * [rightWidths[rightLabel]["bottom"] + rightWidths[rightLabel]["right"]],
            color=colorDict[rightLabel],
            alpha=0.99,
        )
        ax.text(
            1.05 * xMax,
            rightWidths[rightLabel]["bottom"] + 0.5 * rightWidths[rightLabel]["right"],
            rightLabel,
            {"ha": "left", "va": "center"},
            fontsize=fontsize,
        )

    # Plot strips
    for leftLabel in leftLabels:
        for rightLabel in rightLabels:
            labelColor = leftLabel
            if rightColor:
                labelColor = rightLabel
            if (
                len(
                    dataFrame[
                        (dataFrame.left == leftLabel) & (dataFrame.right == rightLabel)
                    ]
                )
                > 0
            ):
                # Create array of y values for each strip, half at left value,
                # half at right, convolve
                ys_d = np.array(
                    50 * [leftWidths[leftLabel]["bottom"]]
                    + 50 * [rightWidths[rightLabel]["bottom"]]
                )
                ys_d = np.convolve(ys_d, 0.05 * np.ones(20), mode="valid")
                ys_d = np.convolve(ys_d, 0.05 * np.ones(20), mode="valid")
                ys_u = np.array(
                    50 * [leftWidths[leftLabel]["bottom"] + ns_l[leftLabel][rightLabel]]
                    + 50
                    * [rightWidths[rightLabel]["bottom"] + ns_r[leftLabel][rightLabel]]
                )
                ys_u = np.convolve(ys_u, 0.05 * np.ones(20), mode="valid")
                ys_u = np.convolve(ys_u, 0.05 * np.ones(20), mode="valid")

                # Update bottom edges at each label so next strip starts at the right place
                leftWidths[leftLabel]["bottom"] += ns_l[leftLabel][rightLabel]
                rightWidths[rightLabel]["bottom"] += ns_r[leftLabel][rightLabel]
                ax.fill_between(
                    np.linspace(0, xMax, len(ys_d)),
                    ys_d,
                    ys_u,
                    alpha=0.65,
                    color=colorDict[labelColor],
                )
    ax.axis("off")
    ax.set_title(
        f"Land cover transitions from {df.columns[0]} to {df.columns[1]}",
        fontweight="bold",
    )
    left, width = -0.001, 0.5
    bottom, height = 0.25, 0.5
    right = left + width
    top = bottom + height

    ax.text(
        left,
        0.5 * (bottom + top),
        df.columns[0],
        horizontalalignment="right",
        verticalalignment="center",
        rotation="vertical",
        alpha=0.15,
        fontsize=50,
        transform=ax.transAxes,
    )
    ax.text(
        1.100,
        0.5 * (bottom + top),
        df.columns[1],
        horizontalalignment="right",
        verticalalignment="center",
        rotation="vertical",
        alpha=0.15,
        fontsize=50,
        transform=ax.transAxes,
    )

    return (fig, ax)


def plot_transition_matrix():
    """Show transition degradation matrix"""

    import matplotlib.colors as colors
    import seaborn as sns

    df = transition_degradation_matrix
    # Pivot the DataFrame to create a transition matrix
    transition_matrix = df.pivot(index="from", columns="to", values="impact_code")

    # Create a custom colormap
    cmap = colors.LinearSegmentedColormap.from_list("", ["red", "gray", "green"])

    # remove legend
    # Create a colored transition matrix using seaborn
    plt.figure(figsize=(6, 4))
    sns.heatmap(transition_matrix, annot=True, cmap=cmap, center=0, cbar=False)
    plt.show()
