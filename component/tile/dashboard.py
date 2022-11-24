from pathlib import Path

import ipyvuetify as v
import sepal_ui.scripts.utils as su
import sepal_ui.sepalwidgets as sw
from ipywidgets import Output
from matplotlib import pyplot as plt
from traitlets import directional_link, link

import component.parameter.directory as DIR
import component.parameter.module_parameter as param
import component.parameter.report_template as rt
import component.scripts as cs
import component.widget as cw
from component.message import cm

__all__ = ["DashboardTile"]


class DashboardTile(v.Layout, sw.SepalWidget):
    def __init__(self, model, *args, **kwargs):

        self.class_ = "d-block"
        self._metadata = {"mount_id": "dashboard_tile"}

        super().__init__(*args, **kwargs)

        self.model = model

        self.dashboard_view = DashboardView(model=self.model).hide()

        self.calculation_view = CalculationView(self.model, self.dashboard_view)
        self.download_task_view = DownloadTaskView(self.model, self.dashboard_view)

        self.report_view = ReportView(self.model)

        self.children = [
            cw.Tabs(
                titles=[
                    "Calculation",
                    "Calculation from Task",
                    "Export results",
                ],
                content=[
                    self.calculation_view,
                    self.download_task_view,
                    self.report_view,
                ],
                class_="mb-2",
            ),
            self.dashboard_view,
        ]


class ReportView(v.Card):
    def __init__(self, model, *args, **kwargs):

        self.class_ = "pa-2"
        super().__init__(*args, **kwargs)

        self.model = model

        self.alert = sw.Alert().add_msg(
            cm.dashboard.report.disabled_alert, type_="warning"
        )

        self.btn = sw.Btn(cm.dashboard.label.download, class_="ml-2", disabled=True)

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
            self.alert,
            self.btn,
        ]

        self.btn.on_event("click", self.download_results)

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
    def download_results(self, *args):
        """Write the results on a comma separated values file, or an excel file"""

        # Generate three reports
        reports = self.model.get_report()
        m49 = cs.get_geoarea(self.model.aoi_model)[1]

        report_filenames = [
            f"{rt.SERIESCOD_GRNCVI}_{m49}.xlsx",
            f"{rt.SERIESCOD_GRNCOV_1}_{m49}.xlsx",
            f"{rt.SERIESCOD_TTL}_{m49}.xlsx",
        ]

        report_folder = cs.get_report_folder(self.model)

        for (
            report,
            report_filename,
        ) in zip(*[reports, report_filenames]):

            report.to_excel(
                str(Path(report_folder, report_filename)),
                sheet_name=report_filename,
                index=False,
            )
        self.alert.add_msg(
            f"The reports were successfully exported in {report_folder}",
            type_="success",
        )


class DownloadTaskView(v.Card):
    def __init__(self, model, dashboard_view, *args, **kwargs):
        """
        Download tile tab: to search and select the tasks_id file, check if the task is
        complete and then download the file.

        """
        self.class_ = "pa-2"

        super().__init__(*args, **kwargs)

        self.model = model
        self.dashboard_view = dashboard_view

        # Widgets
        title = v.CardTitle(children=[cm.dashboard.tasks.title])
        description = v.CardText(
            children=[sw.Markdown(cm.dashboard.tasks.description.format(DIR.TASKS_DIR))]
        )

        question_icon = v.Icon(children=["mdi-help-circle"], small=True)

        self.w_file_input = sw.FileInput(folder=DIR.TASKS_DIR, extentions=[".csv"])

        self.alert = sw.Alert()
        self.btn = sw.Btn(cm.dashboard.label.calculate)

        self.children = [title, description, self.w_file_input, self.btn, self.alert]

        self.btn.on_event("click", self.render_dashboard)

        self.model.bind(self.w_file_input, "task_file")

    @su.loading_button(debug=True)
    def render_dashboard(self, widget, event, data):

        self.dashboard_view.clear()
        self.dashboard_view.render_dashboard(from_task=True)


class CalculationView(v.Card, sw.SepalWidget):
    def __init__(self, model, dashboard_view, rsa=False, *args, **kwargs):

        """Dashboard tile to calculate and resume the zonal statistics for the
        vegetation layer by kapos ranges.

        Args:
            model (MgciModel): Mgci Model

        """

        self.class_ = "pa-2"

        super().__init__(*args, **kwargs)

        self.model = model
        self.calculation = cw.Calculation(self.model)
        self.dashboard_view = dashboard_view

        title = v.CardTitle(children=[cm.dashboard.title])
        description = v.CardText(children=[cm.dashboard.description])

        question_icon = v.Icon(children=["mdi-help-circle"], small=True)

        # widgets
        self.w_use_rsa = v.Switch(
            v_model=self.model.rsa,
            label=cm.dashboard.label.rsa,
            value=True,
        )

        t_rsa = v.Flex(
            class_="d-flex",
            children=[
                sw.Tooltip(
                    self.w_use_rsa, cm.dashboard.help.rsa, right=True, max_width=300
                )
            ],
        )

        # buttons
        self.btn = sw.Btn(cm.dashboard.label.calculate)
        self.alert = sw.Alert()

        self.children = [
            title,
            description,
            self.calculation,
            t_rsa,
            self.btn,
            self.alert,
        ]

        self.model.bind(self.w_use_rsa, "rsa")

        self.btn.on_event("click", self.run_statistics)

    @su.loading_button(debug=True)
    def run_statistics(self, widget, event, data):
        """Start the calculation of the statistics. It will start the process on the fly
        or making a task in the background depending if the rsa is selected or if the
        computation is taking so long.
        """
        # Clear previous loaded results
        self.dashboard_view.clear()

        area_type = (
            cm.dashboard.label.rsa_name
            if self.w_use_rsa.v_model
            else cm.dashboard.label.plan
        )

        # Calculate regions
        self.alert.add_msg(cm.dashboard.alert.computing.format(area_type))

        # It will create the process and store it in reduced_process from model
        self.model.reduce_to_regions()

        if not self.model.rsa:

            # Try the process in on the fly
            try:
                self.model.extract_summary_from_result()
                # self.dashboard_view.render_dashboard()
                self.alert.reset()
            except Exception as e:
                if e.args[0] == "Computation timed out.":
                    name, task_id, task_id_file = self.model.task_process()
                    self.alert.children = [
                        sw.Markdown(
                            cm.dashboard.alert.tasks_failed.format(
                                Path(name).stem, task_id_file
                            )
                        )
                    ]
                else:
                    raise Exception(f"There was an error {e}")
        else:
            name, task_id, task_id_file = self.model.task_process()
            self.alert.children = [
                sw.Markdown(
                    cm.dashboard.alert.tasks_rsa.format(Path(name).stem, task_id_file)
                )
            ]


class DashboardView(v.Card, sw.SepalWidget):
    def __init__(self, model, rsa=False, *args, **kwargs):

        self.class_ = "my-4"

        super().__init__(*args, **kwargs)

        self.model = model
        self.alert = sw.Alert()

        self.children = [self.alert]

    @su.switch("loading")
    def render_dashboard(self, from_task=False):
        """Display results in the dashboard"""

        if from_task:
            self.model.extract_summary_from_result(from_task=True)
        self.show()
        self.alert.add_msg(cm.dashboard.alert.rendering)

        # Get overall MGCI widget
        w_overall = Statistics(self.model)

        # Get individual stats widgets per Kapos classes
        w_individual = [
            Statistics(self.model, krange=krange)
            for krange, row in self.model.summary_df.iterrows()
            if row["krange_area"] != 0
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

        # Reset summary df to clear previous loaded summaries.
        self.model.summary_df = None

        for chld in self.children:
            if isinstance(chld._metadata, dict):
                if "statistics" in chld._metadata.values():
                    self.children = self.children[:-1][:]
                    break


class Statistics(v.Card):
    def __init__(self, model, *args, krange=None, **kwargs):
        """
        Creates a full layout view with a circular MGC index followed by
        horizontal bars of land cover area per kapos classes.

        Args:
            krange (int): kapos range number (1,2,3,4,5,6); empty for overall.
            area_per_class (dictionary): Dictionary of lu/lc areas
        """

        super().__init__(*args, **kwargs)

        self._metadata = {"name": "statistics"}
        self.class_ = "ma-4"
        self.row = True
        self.model = model

        self.output_chart = Output()

        # Create title and description based on the inputs
        title = cm.dashboard.global_.title
        desc = sw.Alert(
            children=[cm.dashboard.global_.desc.format(param.UNITS["sqkm"][1])],
            dense=True,
        ).show()

        if krange:
            title = cm.dashboard.individual.title.format(krange)
            desc = eval(f"cm.dashboard.individual.desc.k{krange}")
        self.children = [
            v.CardTitle(children=[title]),
            v.CardText(children=[desc]),
            v.Row(
                children=[
                    v.Col(
                        sm=4,
                        class_="d-flex justify-center",
                        children=[cs.create_avatar(self.model.get_mgci(krange))],
                    ),
                    v.Col(
                        children=[
                            v.Flex(xs12=True, children=[self.output_chart]),
                        ]
                    ),
                ]
            ),
        ]

        self.get_chart(krange)

    def get_chart(self, krange):

        values = (
            self.model.summary_df.loc[krange][param.DISPLAY_CLASSES]
            if krange
            else self.model.summary_df[param.DISPLAY_CLASSES].sum()
        )

        total_area = values.sum()

        norm_values = [area / total_area * 100 for area in values]
        human_values = [f"{cs.human_format(val)}" for val in values]

        # We are doing this assumming that the dict will create the labels in the
        # same order
        labels, colors = zip(
            *[
                (self.model.lulc_classes[class_][0], self.model.lulc_classes[class_][1])
                for class_ in values.to_dict()
            ]
        )

        with self.output_chart:

            plt.style.use("dark_background")

            # create the chart
            fig, ax = plt.subplots(
                figsize=[25, len(values) * 2], facecolor=((0, 0, 0, 0))
            )

            ax.barh(labels, norm_values, color=colors)

            for i, (norm, name, val, color) in enumerate(
                zip(norm_values, labels, human_values, colors)
            ):
                ax.text(norm + 2, i, val, fontsize=40, color=color)
            # cosmetic tuning

            ax.set_xlim(0, 110)
            ax.tick_params(axis="y", which="major", pad=30, labelsize=40, left=False)
            ax.tick_params(axis="x", bottom=False, labelbottom=False)
            ax.set_frame_on(False)
            plt.show()
