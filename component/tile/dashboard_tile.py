import ipyvuetify as v
import pandas as pd
import sepal_ui.scripts.utils as su
import sepal_ui.sepalwidgets as sw

import component.parameter.module_parameter as param
import component.widget as cw
from component.message import cm
from component.scripts.plots import sankey
from component.scripts.scripts import get_result_from_year
from component.widget.statistics_card import StatisticCard


class DashboardTile(sw.Card):
    def __init__(self, model, rsa=False, *args, **kwargs):
        self.class_ = "my-4"
        self._metadata = {"mount_id": "dashboard_tile"}

        super().__init__(*args, **kwargs)

        self.model = model
        self.alert = sw.Alert()
        self.df = None

        dash_view_a = DashView(self.model, indicator="sub_a")
        dash_view_b = DashView(self.model, indicator="sub_b")

        dash_tabs = cw.Tabs(
            ["Sub indicator A", "Sub indicator B"],
            [dash_view_a, dash_view_b],
        )

        self.children = [
            sw.CardTitle(children=["Results dashboard"]),
            sw.CardText(children=[self.alert, dash_tabs]),
        ]


class DashView(sw.Layout):
    def __init__(self, model, indicator, *args, **kwargs):

        self.indicator = indicator
        self.class_ = "d-block"
        self.attributes = {"id": f"dashboard_view_{self.indicator}"}
        self.model = model

        super().__init__(*args, **kwargs)

        self.alert = sw.Alert()

        self.year_select = sw.Select(label="Select a target year", v_model=None)
        self.btn = sw.Btn("Calculate", class_="ml-2")

        self.children = [
            sw.Flex(
                class_="d-flex align-center",
                children=[self.year_select, self.btn],
            ),
            self.alert,
        ]

        # Observe reporting_a_years from model to update the year_select
        self.model.observe(self.set_years, "reporting_a_years")

        self.btn.on_event("click", self.render_dashboard)

    def clear(self):
        """Check if there is a previusly displayed dashboard and clear it, and
        reset the modeul summary"""
        print("clearing2")

        if self.get_children(id_=f"render_{self.indicator}"):
            self.children = [
                chld
                for chld in self.children
                if chld.attributes.get("id") != f"render_{self.indicator}"
            ]

    def set_years(self, change):
        """Set the years in the year_select"""

        if change["new"]:
            self.year_select.items = list(change["new"].keys())
        else:
            self.year_select.items = []

    @su.loading_button(debug=True)
    def render_dashboard(self):

        self.show()
        self.clear()
        self.alert.add_msg(cm.dashboard.alert.rendering)

        if not self.year_select.v_model:
            raise Exception("Select a year.")

        if self.indicator == "sub_a":
            statistics = self.get_sub_a_dash()
        else:
            statistics = self.get_sub_b_dash()

        self.children + [statistics]
        self.alert.hide()

    def get_sub_a_dash(self, *args):
        """create the corresponding parsed dataframe based on the selected year.
        This dataframe will be used to calculate the MCGI"""

        df = get_result_from_year(self.model, self.year_select.v_model, "sub_a")

        # Get overall MGCI widget
        w_overall = StatisticCard(df, "Total", self.model)

        # Get individual stats widgets per Kapos classes
        w_individual = [
            StatisticCard(df, belt_class, self.model)
            for belt_class in list(df["belt_class"].unique())
        ]

        return sw.Layout(
            attributes={"id": "render_sub_a"},
            class_="d-block",
            children=[w_overall] + w_individual,
        )

    def get_sub_b_dash(self, *args):
        """create the corresponding parsed dataframe based on the selected year.
        This dataframe will be used to calculate the MCGI"""

        df = cs.get_result_from_year(model, "2010_2015", "sub_b")

        # group by from_lc and to_lc
        df_sankey = (
            df[df.belt_class == 4].groupby(["from_lc", "to_lc"], as_index=False).sum()
        )

        # rename columns to match with sankey function
        cols = {"from_lc": "left", "to_lc": "right"}
        df_sankey.rename(columns=cols, inplace=True)

        color_dict = pd.read_csv(param.LC_CLASSES, header=None)
        color_dict = dict(zip(color_dict.loc[:, 0], color_dict.loc[:, 2]))

        output = Output()

        sw.Card(
            children=[
                sw.CardTitle(children=["This is a title"]),
                sw.CardText(children=[output]),
            ]
        )

        with plt.style.context("dark_background"):
            with output:
                output.clear_output()
                fig, ax = sankey(
                    df_sankey,
                    colorDict=color_dict,
                    aspect=4,
                    rightColor=False,
                    fontsize=14,
                )
                display(fig)
