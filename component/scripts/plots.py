from html import escape
from pathlib import Path
from typing import Tuple

import pandas as pd

from ipecharts.echarts import EChartsRawWidget, EChartsWidget
from ipecharts.option import Grid, Legend, Option, Tooltip, XAxis, YAxis
from ipecharts.option.series import Bar, Sankey
from pysepal.solara import get_current_theme_state
from solara.lab.components.theming import theme

import component.parameter.module_parameter as param
from component.scripts.file_handler import read_file


def get_lc_class_map(classes=None):
    """Resolve the active land-cover class labels and colors."""
    classes = classes or param.LC_CLASSES
    if isinstance(classes, (str, Path)):
        return (
            pd.read_csv(classes)
            .set_index("lc_class")[["desc", "color"]]
            .to_dict("index")
        )
    return {
        int(code): {"desc": value[0], "color": value[1]}
        for code, value in classes.items()
    }


class _ThemeBinding:
    """Keep an ipecharts widget aligned with the session's resolved theme."""

    def __init__(self, *args, theme_state=None, theme_updater=None, **kwargs):
        self._theme_observer_registered = False
        self.theme_state = theme_state or get_current_theme_state()
        self.theme_updater = theme_updater
        kwargs.setdefault("theme", "dark" if self.theme_state.dark else "light")
        super().__init__(*args, **kwargs)
        self.theme_state.observe(self._on_theme_change, "dark")
        self._theme_observer_registered = True

    def _on_theme_change(self, change):
        self.theme = "dark" if change["new"] else "light"
        if self.theme_updater:
            self.theme_updater(change["new"])

    def close(self):
        if getattr(self, "_theme_observer_registered", False):
            self._theme_observer_registered = False
            self.theme_state.unobserve(self._on_theme_change, "dark")
        super().close()


class ThemedEChartsWidget(_ThemeBinding, EChartsWidget):
    pass


class ThemedEChartsRawWidget(_ThemeBinding, EChartsRawWidget):
    pass


def get_sankey_chart(theme_state=None):

    sankey_data = Sankey(
        left=20,
        right=20,
        top=8,
        bottom=8,
        nodeWidth=14,
        nodeGap=9,
        label={"show": False},
        lineStyle={"color": "gradient", "curveness": 0.55, "opacity": 0.45},
        emphasis={"focus": "adjacency"},
    )
    sankey_data.nodes = []
    sankey_data.links = []
    option = Option(
        animation=False,
        backgroundColor="transparent",
        series=[sankey_data],
        tooltip=Tooltip(trigger="item"),
    )

    chart = ThemedEChartsWidget(
        option=option,
        theme_state=theme_state,
        renderer="svg",
        style={"height": "390px", "width": "100%"},
    )

    return sankey_data, chart


def get_nodes_and_links(
    df: pd.DataFrame,
    lc_classes_path: str,
    years: Tuple[str, str] = ["from_lc", "to_lc"],
):
    """Generate nodes and links for a Sankey diagram"""

    from_lc, to_lc = [str(y) for y in years]

    desc_color_map = get_lc_class_map(lc_classes_path)

    biobelt_dict = {}

    # Group the dataframe by 'biobelt'
    belt_totals = df.groupby(
        ["belt_class", "from_lc", "to_lc"], as_index=False
    )["sum"].sum()
    totals = belt_totals.groupby(["from_lc", "to_lc"], as_index=False)["sum"].sum()
    totals["belt_class"] = "Total"
    grouped = pd.concat([belt_totals, totals], ignore_index=True).groupby(
        "belt_class", sort=False
    )

    def class_info(code):
        return desc_color_map.get(
            code, {"desc": f"Class {code}", "color": "#888888"}
        )

    def node_name(code, year):
        return f"{code} · {class_info(code)['desc']} · {year}"

    for biobelt, group in grouped:
        nodes = []
        for year, column in [(from_lc, "from_lc"), (to_lc, "to_lc")]:
            for lc_class in sorted(group[column].unique()):
                info = class_info(lc_class)
                nodes.append(
                    {
                        "name": node_name(lc_class, year),
                        "itemStyle": {"color": info["color"]},
                        "tooltip": {
                            "formatter": f"{escape(str(info['desc']))}<br>{year}"
                        },
                    }
                )

        links = []
        for _, row in group.iterrows():
            source_code = int(row["from_lc"])
            target_code = int(row["to_lc"])
            source_info = class_info(source_code)
            target_info = class_info(target_code)
            area = float(row["sum"])
            links.append(
                {
                    "source": node_name(source_code, from_lc),
                    "target": node_name(target_code, to_lc),
                    "value": round(area, 2),
                    "tooltip": {
                        "formatter": (
                            f"{escape(str(source_info['desc']))} ({from_lc}) → "
                            f"{escape(str(target_info['desc']))} ({to_lc})"
                            f"<br><b>{area:,.1f} km²</b>"
                        )
                    },
                }
            )

        # Store nodes and links for this biobelt in the dictionary
        biobelt_dict[biobelt] = {"nodes": nodes, "links": links}

    return biobelt_dict


def get_transition_matrix_chart(
    values, classes=None, theme_state=None, transition_matrix=None
):
    """Show observed area and selected impact for each land-cover transition."""
    labels = get_lc_class_map(classes)
    if isinstance(transition_matrix, pd.DataFrame):
        matrix = transition_matrix
    elif transition_matrix:
        matrix = read_file(transition_matrix)
    else:
        matrix = pd.read_csv(param.TRANSITION_MATRIX_FILE)
    impacts = {
        (int(row.from_code), int(row.to_code)): int(row.impact_code)
        for row in matrix.itertuples(index=False)
    }
    codes = sorted(set(labels) | set(values.from_lc) | set(values.to_lc))
    indices = {code: index for index, code in enumerate(codes)}
    transitions = values.groupby(["from_lc", "to_lc"])["sum"].sum()
    cells = []
    for source in codes:
        for target in codes:
            area = float(transitions.get((source, target), 0.0))
            impact = param.DECODE.get(impacts.get((source, target)))
            color = (
                impact["color"]
                if area > 0 and impact
                else "rgba(128, 138, 142, 0.18)"
            )
            cells.append(
                {
                    "value": [indices[target], indices[source], round(area, 2)],
                    "itemStyle": {"color": color},
                    "tooltip": {
                        "formatter": (
                            f"{escape(labels.get(source, {}).get('desc', f'Class {source}'))}"
                            f" → {escape(labels.get(target, {}).get('desc', f'Class {target}'))}"
                            f"<br>{impact['label'] if impact else 'Unclassified'}"
                            f"<br><b>{area:,.1f} km²</b>"
                        )
                    },
                }
            )

    state = theme_state or get_current_theme_state()
    dark = state.dark

    def border_style(is_dark):
        return {"borderWidth": 2, "borderColor": "#252a2d" if is_dark else "#fff"}

    option = {
        "backgroundColor": "transparent",
        "grid": {"left": 48, "right": 24, "top": 42, "bottom": 45},
        "xAxis": {
            "type": "category",
            "data": [str(code) for code in codes],
            "position": "top",
            "axisTick": {"show": False},
            "axisLine": {"show": False},
        },
        "yAxis": {
            "type": "category",
            "data": [str(code) for code in codes],
            "inverse": True,
            "axisTick": {"show": False},
            "axisLine": {"show": False},
        },
        "series": [{"type": "heatmap", "data": cells, "itemStyle": border_style(dark)}],
        "tooltip": {"trigger": "item"},
    }

    def update_theme(is_dark):
        updated = dict(chart.option)
        updated["series"] = [
            {**updated["series"][0], "itemStyle": border_style(is_dark)}
        ]
        chart.option = updated

    chart = ThemedEChartsRawWidget(
        option=option,
        theme_state=state,
        theme_updater=update_theme,
        renderer="svg",
        style={"height": "440px", "width": "100%"},
    )
    return chart


def get_land_cover_bar_chart(values, classes):
    """Compact, directly labeled land-cover shares."""
    values = values.groupby("lc_class", as_index=False)["sum"].sum()
    values = values[values["sum"] > 0].sort_values("sum", ascending=False)
    total_area = values["sum"].sum()
    labels = []
    data = []
    for _, row in values.iterrows():
        code = row["lc_class"]
        class_info = classes.get(code, classes.get(str(code)))
        if class_info is None:
            class_info = [f"Class {code}", "#888888"]
        name, color = class_info[:2]
        labels.append(name)
        percentage = round(row["sum"] / total_area * 100, 1) if total_area else 0
        data.append(
            {
                "name": name,
                "value": percentage,
                "itemStyle": {"color": color, "borderRadius": [0, 5, 5, 0]},
                "tooltip": {
                    "formatter": (
                        f"{escape(str(name))}<br><b>{percentage:.1f}%</b> "
                        f"· {row['sum']:,.1f} km²"
                    )
                },
            }
        )

    dark = bool(theme.dark)
    option = Option(
        backgroundColor="transparent",
        grid=Grid(left=205, right=62, top=8, bottom=8),
        xAxis=XAxis(type="value", min=0, max=100, show=False),
        yAxis=YAxis(
            type="category",
            data=labels,
            inverse=True,
            axisLine={"show": False},
            axisTick={"show": False},
            axisLabel={"fontSize": 12, "width": 185, "overflow": "truncate"},
        ),
        series=[
            Bar(
                data=data,
                barWidth=14,
                showBackground=True,
                backgroundStyle={
                    "color": "#353b40" if dark else "#edf0f2",
                    "borderRadius": 5,
                },
                label={"show": True, "position": "right", "formatter": "{c}%"},
            )
        ],
        tooltip=Tooltip(trigger="item"),
    )
    return EChartsWidget(
        option=option,
        theme="dark" if dark else "light",
        renderer="svg",
        style={"height": f"{max(150, len(labels) * 29 + 24)}px", "width": "100%"},
    )


def get_series_data(df):
    """Generate series data for a bar chart."""

    series_data = []
    for col in df.columns:
        if col == "year":
            continue
        series_data.append(
            {
                "name": col,
                "data": df[col].tolist(),
                "itemStyle": {"color": "#5f8b95"},
            }
        )
    return series_data


def get_bars(series_data):
    """Create a list of bar series from the series data."""
    bars = []
    for series in series_data:
        bars.append(
            Bar(
                **{
                    "type": "bar",
                    "name": series["name"],
                    "stack": True,
                    "data": series["data"],
                    "itemStyle": series["itemStyle"],
                }
            )
        )
    return bars


def get_chart(df):

    landcov_names, series_data = get_series_data(df)
    bars = get_bars(series_data)

    option = Option(
        backgroundColor="#1e1e1e00",
        legend=Legend(data=landcov_names),
        yAxis=YAxis(type="category", data=landcov_names),
        xAxis=XAxis(type="value"),
        series=bars,
        tooltip=Tooltip(),
    )
    return EChartsWidget(option=option)
