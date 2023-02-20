import ipyvuetify as v
import sepal_ui.scripts.utils as su
import sepal_ui.sepalwidgets as sw

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

        self.year_select = sw.Select(label="Select a target year", v_model=None)
        self.btn = sw.Btn("Calculate", class_="ml-2")

        self.children = [
            sw.CardTitle(children=["Results dashboard"]),
            sw.CardText(
                children=[
                    sw.Flex(
                        class_="d-flex align-center",
                        children=[self.year_select, self.btn],
                    ),
                    self.alert,
                ]
            ),
        ]

        self.btn.on_event("click", self.render_dashboard)

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

    @su.switch("loading")
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

        statistics = v.Layout(
            class_="d-block",
            children=[w_overall] + w_individual,
            _metadata={"name": "statistics"},
        )

        new_items = self.children + [statistics]

        self.children = new_items
        self.alert.hide()

    def clear(self):
        """Check if there is a previusly displayed dashboard and clear it, and
        reset the modeul summary"""

        for chld in self.children:
            if isinstance(chld._metadata, dict):
                if "statistics" in chld._metadata.values():
                    self.children = self.children[:-1][:]
                    break
