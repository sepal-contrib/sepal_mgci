import ipyvuetify as v
import sepal_ui.scripts.utils as su
import sepal_ui.sepalwidgets as sw

import component.widget as cw
from component.message import cm
from component.scripts.scripts import parse_result
from component.widget.statistics_card import StatisticCard


class DashboardTile(sw.Card):
    def __init__(self, model, rsa=False, *args, **kwargs):
        self.class_ = "my-4"
        self._metadata = {"mount_id": "dashboard_tile"}

        super().__init__(*args, **kwargs)

        self.model = model
        self.alert = sw.Alert()
        self.df = None

        dash_view_a = DashViewA(self.model)
        dash_view_b = DashViewB(self.model)

        dash_tabs = cw.Tabs(
            ["Sub indicator A", "Sub indicator B"],
            [dash_view_a, dash_view_b],
        )

        self.children = [
            sw.CardTitle(children=["Results dashboard"]),
            sw.CardText(children=[self.alert, dash_tabs]),
        ]

        self.model.observe(self.get_years, "done")

    def get_years(self, change):
        if change["new"]:
            # Search year, consider it might be in yyyy_yyyy format.
            years = [
                year
                for year_s in list(self.model.results.keys())
                for year in year_s.split("_")
            ]
        else:
            years = []

        self.clear()
        self.year_select.items = years


class DashViewA(sw.Layout):
    def __init__(self, model, *args, **kwargs):

        self.attributes = {"id": "dashboard_view_sub_a"}
        self.model = model
        self.children = []

        super().__init__(*args, **kwargs)

        self.year_select = sw.Select(label="Select a target year", v_model=None)
        self.btn = sw.Btn("Calculate", class_="ml-2")
        self.btn.on_event("click", self.render_dashboard)

    @su.loading_button(debug=True)
    def render_dashboard(self, *args):
        """create the corresponding parsed dataframe based on the selected year.
        This dataframe will be used to calculate the MCGI"""

        self.show()
        self.clear()
        self.alert.add_msg(cm.dashboard.alert.rendering)

        if not self.year_select.v_model:
            raise Exception("Select a year.")

        lookup_year = self.year_select.v_model
        group_name = [
            group for group in list(self.model.results.keys()) if lookup_year in group
        ][0]

        if len(group_name.split("_")) > 1:
            df = parse_result(self.model.results[group_name]["groups"], single=False)
            target_lc = ["from_lc", "to_lc"][group_name.split("_").index(lookup_year)]
            cols = ["belt_class", target_lc]
            df = df.groupby(cols, as_index=False).sum()[cols + ["sum"]]
            df = df.rename(columns={target_lc: "lc_class"})

        else:
            df = parse_result(self.model.results[group_name]["groups"], single=True)

        # Get overall MGCI widget
        w_overall = StatisticCard(df, "Total", self.model)

        # Get individual stats widgets per Kapos classes
        w_individual = [
            StatisticCard(df, belt_class, self.model)
            for belt_class in list(df["belt_class"].unique())
        ]

        statistics = sw.Layout(
            attributes={"name": "render_sub_a"},
            class_="d-block",
            children=[w_overall] + w_individual,
        )

        new_items = self.children + [statistics]

        self.children = new_items
        self.alert.hide()

    def clear(self):
        """Check if there is a previusly displayed dashboard and clear it, and
        reset the modeul summary"""

        if self.get_children(id_="render_sub_a"):
            self.children = [
                chld
                for chld in self.children
                if chld.attributes["name"] != "render_sub_a"
            ]


class DashViewB(sw.Layout):
    def __init__(self, model, *args, **kwargs):

        self.attributes = {"id": "dashboard_view_sub_b"}
        self.model = model
        self.children = []

        super().__init__(*args, **kwargs)
