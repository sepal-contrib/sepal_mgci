from IPython.display import display
import ipyvuetify as v
import pandas as pd
import sepal_ui.scripts.utils as su
import sepal_ui.sepalwidgets as sw
from ipywidgets import Output
from matplotlib import pyplot as plt
from traitlets import link
from component.model.model import MgciModel

import component.parameter.module_parameter as param
import component.scripts as cs
from component.scripts.validation import validate_sankey_classes
import component.widget as cw
from component.message import cm
from component.scripts.plots import (
    get_nodes_and_links,
    get_pyecharts_sankey,
    get_sankey_chart,
    sankey,
)
from component.scripts.report_scripts import get_belt_desc
from component.widget.map import MapView
from component.widget.statistics_card import StatisticCard


class DashboardTile(sw.Card):
    def __init__(self, model, rsa=False, *args, **kwargs):
        self.class_ = "my-4"
        self._metadata = {"mount_id": "dashboard_tile"}

        super().__init__(*args, **kwargs)

        self.model = model
        self.alert = sw.Alert()
        self.df = None

        map_view = MapView(self.model)
        dash_view_a = DashViewA(self.model)
        dash_view_b = DashViewB(self.model)
        self.dash_view_b = dash_view_b

        dash_tabs = cw.Tabs(
            ["Visualization", "Sub indicator A", "Sub indicator B"],
            [map_view, dash_view_a, dash_view_b],
        )

        self.children = [
            sw.CardTitle(children=["Results dashboard"]),
            sw.CardText(children=[self.alert, dash_tabs]),
        ]


class DashView(sw.Layout):
    def __init__(self, indicator, model, *args, **kwargs):
        self.indicator = indicator
        self.class_ = "d-block pa-2"

        self.model = model

        super().__init__(*args, **kwargs)

    def clear(self):
        """Check if there is a previusly displayed dashboard and clear it, and
        reset the modeul summary"""

        if self.get_children(id_=f"render_{self.indicator}"):
            self.children = [
                chld
                for chld in self.children
                if chld.attributes.get("id") != f"render_{self.indicator}"
            ]

    def render_dashboard(self, *args):
        """create the corresponding parsed dataframe based on the selected year."""

        self.show()
        self.clear()
        self.alert.add_msg(cm.dashboard.alert.rendering)

        if not self.year_select.v_model:
            raise Exception("Select a year.")

        if not self.model.results:
            raise Exception(
                "No results to display, go to the calculation step and perform the calculation first."
            )


class DashViewA(DashView):
    def __init__(self, model, *args, **kwargs):
        self.attributes = {"id": f"dashboard_view_sub_a"}

        super().__init__(indicator="sub_a", model=model, *args, **kwargs)

        self.alert = sw.Alert()

        self.year_select = sw.Select(
            class_="mr-2", label="Select a target year", v_model=None
        )
        self.btn = sw.Btn("Calculate", class_="ml-2")

        self.children = [
            sw.Flex(
                class_="d-flex align-center",
                children=[self.year_select, self.btn],
            ),
            self.alert,
        ]

        # Observe reporting_years_{indicator} from model to update the year_select

        self.model.observe(self.set_years, f"reporting_years_sub_a")

        self.btn.on_event("click", self.render_dashboard)

        self.set_years({"new": self.model.reporting_years_sub_a})

    def set_years(self, change):
        """Set the years in the year_select"""

        if change["new"].keys():
            self.year_select.items = list(change["new"].keys())
        else:
            self.year_select.items = []

    @su.loading_button()
    def render_dashboard(self, *args):
        """create the corresponding parsed dataframe based on the selected year.
        This dataframe will be used to calculate the MCGI"""

        super().render_dashboard()

        df = cs.parse_to_year_a(
            self.model.results,
            self.model.reporting_years_sub_a,
            self.year_select.v_model,
        )

        # Get overall MGCI widget
        w_overall = StatisticCard(df, "Total", self.model)

        # Get individual stats widgets per Kapos classes
        w_individual = [
            StatisticCard(df, belt_class, self.model)
            for belt_class in list(df["belt_class"].unique())
        ]

        statistics = sw.Layout(
            attributes={"id": "render_sub_a"},
            class_="d-block",
            children=[w_overall] + w_individual,
        )

        self.children = self.children + [statistics]
        self.alert.hide()


class DashViewB(DashView):
    def __init__(self, model, *args, **kwargs):
        self.attributes = {"id": "dashboard_view_sub_b"}

        super().__init__(indicator="sub_b", model=model, *args, **kwargs)

        self.year_select = sw.Select(
            style_="max-width: 300px",
            class_="mr-2",
            label="Select a target year",
            v_model=None,
        )
        self.belt_select = sw.Select(class_="mr-2", label="Select a belt", v_model=None)

        self.sankey_data, self.chart = get_sankey_chart()

        self.children = [
            sw.Flex(
                class_="d-flex align-center",
                children=[self.year_select, self.belt_select],
            ),
            self.chart,
        ]

        # Observe reporting_years_{indicator} from model to update the year_select

        self.model.observe(self.set_years, "reporting_years_sub_b")
        self.year_select.observe(self.set_belt_items, "v_model")
        self.belt_select.observe(self.update_sankey_data, "v_model")

        self.set_years({"new": self.model.reporting_years_sub_b})

    def set_belt_items(self, change):
        """Set the belt items in the belt_select widget based on the year selected

        Args:
            change["new"]: year selected in the form:
                {"baseline": [year1, year2]} or,
                {"report": [base_start, report_year]}
        """

        look_up_year = change["new"]

        df = cs.parse_to_year(self.model.results, look_up_year)
        look_up_years = list(look_up_year.values())[0]
        self.nodes_and_links = get_nodes_and_links(df, param.LC_CLASSES, look_up_years)

        # Get all belts that are available for the selected year

        belt_items = [
            {"text": get_belt_desc(row), "value": row.belt_class}
            for _, row in pd.DataFrame(
                df.belt_class.unique(), columns=["belt_class"]
            ).iterrows()
        ]

        self.belt_select.items = belt_items
        self.belt_select.v_model = None
        self.belt_select.v_model = belt_items[0]["value"]

    def set_years(self, change):
        """Set the years in the year_select:

        Args:
            change["new]: List of years in the form:
                [[start_base_y, end_base_y], rep_y2, rep_y2, ...]
        """

        if change["new"]:
            items, _ = cs.get_sub_b_items(change["new"])
            self.year_select.items = items
        else:
            self.year_select.items = []

    def update_sankey_data(self, change):
        """create the corresponding parsed dataframe based on the selected year.
        This dataframe will be used to calculate the MCGI"""

        if not change["new"]:
            return

        belt_data = self.nodes_and_links[change["new"]]

        self.sankey_data.nodes = belt_data["nodes"]
        self.sankey_data.links = belt_data["links"]
