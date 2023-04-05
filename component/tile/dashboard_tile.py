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

        # Observe reporting_years_{indicator} from model to update the year_select

        self.model.observe(self.set_years, f"reporting_years_{self.indicator}")

        self.btn.on_event("click", self.render_dashboard)

    def clear(self):
        """Check if there is a previusly displayed dashboard and clear it, and
        reset the modeul summary"""

        if self.get_children(id_=f"render_{self.indicator}"):
            self.children = [
                chld
                for chld in self.children
                if chld.attributes.get("id") != f"render_{self.indicator}"
            ]

    def set_years(self, change):
        """Set the years in the year_select"""

        value = change["new"].keys() if self.indicator == "sub_a" else change["new"]

        if value:
            self.year_select.items = list(value)
        else:
            self.year_select.items = []

    @su.loading_button(debug=True)
    def render_dashboard(self, *_):

        self.show()
        self.clear()
        self.alert.add_msg(cm.dashboard.alert.rendering)

        if not self.year_select.v_model:
            raise Exception("Select a year.")

        if self.indicator == "sub_a":
            statistics = self.get_sub_a_dash()
        else:
            statistics = self.get_sub_b_dash()

        self.children = self.children + [statistics]

        self.alert.hide()

    def get_sub_a_dash(self, *args):
        """create the corresponding parsed dataframe based on the selected year.
        This dataframe will be used to calculate the MCGI"""

        df = cs.get_result_from_year(self.model, self.year_select.v_model, "sub_a")

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

        # Receive user year selection.
        # search for the corresponding base&report tuple in the model
        # retrieve actual tuple 'base_report' that was calculated and it's stored
        # in model.results

        look_up_year = self.year_select.v_model

        sub_b_label = cs.get_sub_b_years_labels(self.model.sub_b_year)[look_up_year]

        df = cs.get_result_from_year(self.model, sub_b_label, "sub_b")

        # group by from_lc and to_lc
        df_sankey = (
            df[df.belt_class == 4].groupby(["from_lc", "to_lc"], as_index=False).sum()
        )

        lbl_left, lbl_right = sub_b_label.split("_")

        # rename columns to match with sankey function
        cols = {"from_lc": lbl_left, "to_lc": lbl_right}

        df_sankey.rename(columns=cols, inplace=True)

        color_dict = pd.read_csv(param.LC_CLASSES, header=None)
        color_dict = dict(zip(color_dict.loc[:, 0], color_dict.loc[:, 2]))

        output = Output()

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

        return sw.Layout(
            attributes={"id": "render_sub_b"},
            class_="d-block",
            children=[
                sw.CardText(children=[output]),
            ],
        )


class ExportView(v.Card):
    def __init__(self, model, *args, **kwargs):
        self.class_ = "pa-2"
        super().__init__(*args, **kwargs)

        self.model = model
        self.attributes = {"id": "report_view"}

        self.alert = sw.Alert().add_msg(
            cm.dashboard.report.disabled_alert, type_="warning"
        )

        self.btn = sw.Btn(cm.dashboard.label.download, class_="ml-2", disabled=False)

        self.w_year = v.TextField(
            label=cm.dashboard.label.year,
            v_model=self.model.year,
            type="string",
        )

        self.w_source = v.TextField(
            label=cm.dashboard.label.source,
            v_model=self.model.source,
            type="string",
        )

        question_icon = v.Icon(children=["mdi-help-circle"], small=True)

        # Create tooltip
        t_year = v.Flex(
            class_="d-flex",
            children=[
                self.w_year,
                sw.Tooltip(
                    question_icon, cm.dashboard.help.year, left=True, max_width=300
                ),
            ],
        )

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
                    )
                ]
            ),
            t_year,
            t_source,
            self.btn,
            self.alert,
        ]

        self.btn.on_event("click", self.export_results)

        # We need a two-way-binding for the year
        link((self.w_year, "v_model"), (self.model, "year"))

        self.model.bind(self.w_source, "source")
        self.model.observe(self.activate_download, "summary_df")

    def activate_download(self, change):
        """Verify if the summary_df is created, and activate button"""

        if change["new"] is not None:
            self.btn.disabled = False
            self.alert.reset()
        else:
            self.btn.disabled = True
            self.alert.add_msg(cm.dashboard.report.disabled_alert, type_="warning")

    @su.loading_button(debug=True)
    def export_results(self, *args):
        """Write the results on a comma separated values file, or an excel file"""

        self.alert.add_msg("Exporting tables...")

        cs.get_geoarea(self.model.aoi_model)[1]
        report_folder = cs.get_report_folder(self.model)
        cs.export_reports(self.model, report_folder)

        self.alert.add_msg(
            f"Reporting tables successfull exported {report_folder}", type_="success"
        )
