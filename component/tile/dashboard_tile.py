import ipyvuetify as v
import pandas as pd
import sepal_ui.scripts.utils as su
import sepal_ui.sepalwidgets as sw
from ipywidgets import Output
from matplotlib import pyplot as plt
from traitlets import link

import component.parameter.module_parameter as param
import component.scripts as cs
import component.widget as cw
from component.message import cm
from component.scripts.plots import sankey
from component.scripts.report_scripts import get_belt_desc
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
        export_view = ExportView(self.model)

        dash_tabs = cw.Tabs(
            ["Sub indicator A", "Sub indicator B", "Export results"],
            [dash_view_a, dash_view_b, export_view],
        )

        self.children = [
            sw.CardTitle(children=["Results dashboard"]),
            sw.CardText(children=[self.alert, dash_tabs]),
        ]


class DashView(sw.Layout):
    def __init__(self, indicator, *args, **kwargs):
        self.indicator = indicator

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


class DashViewA(DashView):
    def __init__(self, model, *args, **kwargs):
        self.class_ = "d-block"
        self.attributes = {"id": f"dashboard_view_sub_a"}
        self.model = model

        super().__init__(indicator="sub_a", *args, **kwargs)

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

    def set_years(self, change):
        """Set the years in the year_select"""

        if change["new"].keys():
            self.year_select.items = list(change["new"].keys())
        else:
            self.year_select.items = []

    @su.loading_button(debug=True)
    def render_dashboard(self, *args):
        """create the corresponding parsed dataframe based on the selected year.
        This dataframe will be used to calculate the MCGI"""

        if not self.year_select.v_model:
            raise Exception("Select a year.")

        self.show()
        self.clear()
        self.alert.add_msg(cm.dashboard.alert.rendering)

        df = cs.get_result_from_year(self.model, self.year_select.v_model, "sub_a")

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
        self.class_ = "d-block"
        self.attributes = {"id": "dashboard_view_sub_b"}
        self.model = model

        super().__init__(indicator="sub_b", *args, **kwargs)

        self.alert = sw.Alert()

        self.year_select = sw.Select(
            class_="mr-2", label="Select a target year", v_model=None
        )
        self.belt_select = sw.Select(class_="mr-2", label="Select a belt", v_model=None)

        self.btn = sw.Btn("Calculate", class_="ml-2")

        self.children = [
            sw.Flex(
                class_="d-flex align-center",
                children=[self.year_select, self.belt_select, self.btn],
            ),
            self.alert,
        ]

        # Observe reporting_years_{indicator} from model to update the year_select

        self.model.observe(self.set_years, "reporting_years_sub_b")
        self.btn.on_event("click", self.render_dashboard)
        self.year_select.observe(self.set_belt_items, "v_model")

    def set_belt_items(self, change):
        """Set the belt items in the belt_select widget based on the year selected"""

        look_up_year = change["new"]

        self.sub_b_label = cs.get_sub_b_years_labels(self.model.sub_b_year)[
            look_up_year
        ]
        search_year = self.sub_b_label

        self.df = cs.get_result_from_year(self.model, search_year, self.indicator)

        # Get all belts that are available for the selected year

        # Create items for the belt_select widget as list of dictionaries containing
        # {"text": get_belt_desc, "value": belt_class}

        belt_items = [
            {"text": get_belt_desc(row), "value": row.belt_class}
            for idx_, row in pd.DataFrame(
                self.df.belt_class.unique(), columns=["belt_class"]
            ).iterrows()
        ]

        self.belt_select.items = belt_items

    def set_years(self, change):
        """Set the years in the year_select"""

        if change["new"]:
            self.year_select.items = list(change["new"])
        else:
            self.year_select.items = []

    @su.loading_button(debug=True)
    def render_dashboard(self, *args):
        """create the corresponding parsed dataframe based on the selected year.
        This dataframe will be used to calculate the MCGI"""

        self.show()
        self.clear()
        self.alert.add_msg(cm.dashboard.alert.rendering)

        if not self.year_select.v_model:
            raise Exception("Select a year.")

        # Receive user year selection.
        # search for the corresponding base&report tuple in the model
        # retrieve actual tuple 'base_report' that was calculated and it's stored
        # in model.results

        self.df_sankey = (
            self.df[self.df.belt_class == self.belt_select.v_model]
            .groupby(["from_lc", "to_lc"], as_index=False)
            .sum()
        )

        color_dict = pd.read_csv(param.LC_CLASSES)

        color_dict = dict(
            zip(color_dict.loc[:, "lc_class"], color_dict.loc[:, "color"])
        )

        output = Output()

        # rename columns to match with sankey function
        lbl_left, lbl_right = self.sub_b_label.split("_")
        cols = {"from_lc": lbl_left, "to_lc": lbl_right}
        self.df_sankey.rename(columns=cols, inplace=True)

        with plt.style.context("dark_background"):
            with output:
                output.clear_output()
                fig, ax = sankey(
                    self.df_sankey,
                    colorDict=color_dict,
                    aspect=4,
                    rightColor=False,
                    fontsize=14,
                )
                display(fig)

        statistics = sw.Layout(
            attributes={"id": "render_sub_b"},
            class_="d-block",
            children=[
                sw.CardText(children=[output]),
            ],
        )

        self.children = self.children + [statistics]

        self.alert.hide()


class ExportView(v.Card):
    def __init__(self, model, *args, **kwargs):
        self.class_ = "pa-2"
        super().__init__(*args, **kwargs)

        self.model = model
        self.attributes = {"id": "report_view"}

        self.alert = sw.Alert()

        self.btn = sw.Btn(cm.dashboard.label.download, class_="ml-2", disabled=False)

        self.w_source = v.TextField(
            label=cm.dashboard.label.source,
            v_model=self.model.source,
            type="string",
        )

        question_icon = v.Icon(children=["mdi-help-circle"], small=True)

        t_source = v.Flex(
            class_="d-flex",
            children=[
                self.w_source,
                sw.Tooltip(
                    question_icon, cm.dashboard.help.source, left=True, max_width=300
                ),
            ],
        )

        self.children = [
            v.CardTitle(children=[cm.dashboard.report.title]),
            v.CardText(
                children=[
                    sw.Markdown(
                        cm.dashboard.report.description.format(*param.UNITS["sqkm"][1])
                    ),
                    t_source,
                ]
            ),
            self.btn,
            self.alert,
        ]

        self.btn.on_event("click", self.export_results)
        self.model.observe(self.activate_download, "summary_df")

        link((self.model, "source"), (self.w_source, "v_model"))

    def activate_download(self, change):
        """Verify if the summary_df is created, and activate button"""

        if change["new"] is not None:
            self.btn.disabled = False
            self.alert.reset()

    @su.loading_button(debug=True)
    def export_results(self, *args):
        """Write the results on a comma separated values file, or an excel file"""

        self.alert.add_msg("Exporting tables...")

        report_folder = cs.get_report_folder(self.model)
        cs.export_reports(self.model, report_folder)

        self.alert.add_msg(
            f"Reporting tables successfull exported {report_folder}", type_="success"
        )
