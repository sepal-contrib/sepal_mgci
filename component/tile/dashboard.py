from pathlib import Path
from matplotlib import pyplot as plt

from traitlets import directional_link, link
from ipywidgets import Output
import ipyvuetify as v

import sepal_ui.sepalwidgets as sw
from sepal_ui.scripts.utils import loading_button, switch

import component.parameter.report_template as rt
import component.parameter as param
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
        self.dashboard_view = DashboardView(model=self.model)
        self.report_view = ReportView(model=self.model)

        self.children = [
            cw.Tabs(
                titles=["Calculation", "Generate report"],
                content=[self.dashboard_view, self.report_view],
            )
        ]


class ReportView(v.Card):
    def __init__(self, model, *args, **kwargs):

        self.class_ = "pa-2"
        super().__init__(*args, **kwargs)

        self.model = model

        self.alert = sw.Alert()

        self.download_btn = sw.Btn(
            cm.dashboard.label.download, class_="ml-2", disabled=True
        )

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
            v.CardText(children=[sw.Markdown(cm.dashboard.report.description)]),
            t_year,
            t_source,
            self.download_btn,
            self.alert,
        ]

        self.download_results = loading_button(
            alert=self.alert, button=self.download_btn, debug=True
        )(self.download_results)

        self.download_btn.on_event("click", self.download_results)

        # We need a two-way-binding for the year
        link((self.w_year, "v_model"), (self.model, "year"))

        self.model.bind(self.w_source, "source")
        self.model.observe(self.activate_download, "reduce_done")

    def activate_download(self, change):
        """Verify if the calculation is done, and activate button"""
        if change["new"]:
            self.download_btn.disabled = False
        else:
            self.download_btn.disabled = True

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

        for report, report_filename, in zip(*[reports, report_filenames]):
            
            report.to_excel(
                str(Path(report_folder, report_filename)),
                sheet_name=report_filename,
                index=False,
            )
            
        self.alert.add_msg(
            f"The reports were successfully exported in {report_folder}",
            type_="success",
        )


class DashboardView(v.Card, sw.SepalWidget):
    def __init__(self, model, rsa=False, *args, **kwargs):

        """Dashboard tile to calculate and resume the zonal statistics for the 
        vegetation layer by kapos ranges.
        
        Args:
            model (MgciModel): Mgci Model
            
        """

        self.class_ = "pa-2"

        super().__init__(*args, **kwargs)

        self.model = model

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
            t_rsa,
            self.btn,
            self.alert,
        ]

        self.model.bind(self.w_use_rsa, "rsa")

        # Decorate functions
        self.get_dashboard = loading_button(
            alert=self.alert, button=self.btn, debug=True
        )(self.get_dashboard)

        self.btn.on_event("click", self.get_dashboard)

    def get_dashboard(self, widget, event, data):
        """Create dashboard"""

        # Remove previusly dashboards
        if self.is_displayed():
            self.children = self.children[:-1][:]
        area_type = (
            cm.dashboard.label.rsa_name
            if self.w_use_rsa.v_model
            else cm.dashboard.label.plan
        )

        # Calculate regions
        self.alert.add_msg(cm.dashboard.alert.computing.format(area_type))
        
        
        def task_result():
            
            # The process will take so long. Create a task in gee.
            task = self.model.task_result()
        
        if not self.model.rsa:
            
            try:
                self.model.extract_summary_from_result()
            
            except:
                
            
        else:

        if self.model.rsa:

            
            # TODO: Store task id
            self.alert.add_msg(
                f"The calculation is being executed in GEE. You can track its process, "
                f"by using the task id: {task.id}"
            )
            # Create an alert to store the taskId
            return
        else:
            try:
                # We will use the coarser resolution, so it will finish the process
                # on the fly
                self.model.extract_summary_from_result(result)
            except:
                
        self.alert.append_msg(cm.dashboard.alert.rendering)

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

    def is_displayed(self):
        """Check if there is a previusly displayed dashboard"""

        for chld in self.children:
            if isinstance(chld._metadata, dict):
                if "statistics" in chld._metadata.values():
                    return True
        return False


class Statistics(v.Card):
    def __init__(self, model, *args, krange=None, **kwargs):
        super().__init__(*args, **kwargs)

        """
        Creates a full layout view with a circular MGC index followed by 
        horizontal bars of land cover area per kapos classes.
        
        Args:
            krange (int): kapos range number (1,2,3,4,5,6); empty for overall.
            area_per_class (dictionary): Dictionary of lu/lc areas             
        """
        
        self._metadata = {"name": "statistics"}
        self.class_ = "ma-4"
        self.row = True
        self.model = model

        self.output_chart = Output()

        # Create title and description based on the inputs
        title = cm.dashboard.global_.title
        desc = sw.Alert(
            children=[cm.dashboard.global_.desc.format(param.UNITS['sqkm'][1])],
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
