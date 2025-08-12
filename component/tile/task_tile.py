from pathlib import Path

import ipyvuetify as v
import sepal_ui.scripts.utils as su
import sepal_ui.sepalwidgets as sw
from sepal_ui.scripts.sepal_client import SepalClient
from sepal_ui.sepalwidgets.file_input import FileInput
from sepal_ui.scripts.drive_interface import GDriveInterface
from sepal_ui.scripts.gee_interface import GEEInterface

from component.parameter.directory import dir_
import component.scripts as cs
import component.widget as cw
from component.message import cm
from component.scripts.file_handler import read_file
from component.scripts.gdrive import download_from_task_file


class DownloadTaskView(v.Card):
    def __init__(
        self,
        sepal_client: SepalClient = None,
        drive_interface: GDriveInterface = None,
        gee_interface: GEEInterface = None,
        *args,
        **kwargs,
    ):
        """
        Download tile tab: to search and select the tasks_id file, check if the task is
        complete and then download the file.

        """
        self.class_ = "ma-0 pa-0"
        self.elevation = 0
        self.sepal_client = sepal_client
        self.drive_interface = drive_interface
        self.gee_interface = gee_interface

        super().__init__(*args, **kwargs)

        # Widgets
        title = v.CardTitle(children=[cm.dashboard.tasks.title], class_="px-0 mx-0")
        description = sw.Markdown(cm.dashboard.tasks.description.format(dir_.tasks_dir))
        description.class_ = "pa-0 ma-0"
        description.max_width = "400px"

        v.Icon(children=["mdi-help-circle"], small=True)

        self.w_file_input = FileInput(
            initial_folder=str(dir_.tasks_dir),
            extensions=[".json"],
            root=str(dir_.results_dir),
            sepal_client=sepal_client,
        )

        self.alert = sw.Alert()

        self.btn = sw.Btn(cm.dashboard.label.calculate_from_task, small=True)

        self.children = [
            title,
            description,
            self.w_file_input,
            self.btn,
            self.alert,
        ]

        self.btn.on_event("click", self.run_statistics)

    @su.loading_button()
    def run_statistics(self, *_):
        """From the gee result dictionary, extract the values and give a proper
        format in a pd.DataFrame.

        Args:
            process (ee.reduceRegion): ee process (without execution).
            task_file (path, str): full path of task file containing task_id(s)
        """

        # Get and read file
        tasks_file = self.w_file_input.v_model

        tasks_file = Path(tasks_file)

        data = read_file(tasks_file)

        # Task
        task_id = data["task"]["id"]
        task_name = data["task"]["name"]

        # Model state
        reporting_years_sub_a = data["model_state"]["reporting_years_sub_a"]
        sub_b_year = data["model_state"]["sub_b_year"]
        geo_area_name = data["model_state"]["geo_area_name"]
        ref_area = data["model_state"]["ref_area"]
        source_detail = data["model_state"]["source_detail"]
        transition_matrix = data["model_state"]["transition_matrix"]
        report_folder = Path(data["model_state"]["report_folder"])

        # make sure the report folder exists
        report_folder = cs.create_folder(report_folder, sepal_client=self.sepal_client)

        session_id = data["model_state"]["session_id"]

        # reporting_years_sub_a always have to be inteners
        reporting_years_sub_a = {
            int(key): value for key, value in reporting_years_sub_a.items()
        }

        # re-build the filename
        task_filename = f"{tasks_file.stem}.csv"

        # Dowload from file
        msg = cw.TaskMsg(f"Processing {task_filename}..", session_id)
        self.alert.append_msg(msg)

        result_file = download_from_task_file(
            task_id,
            tasks_file,
            task_filename,
            drive_interface=self.drive_interface,
            gee_interface=self.gee_interface,
            sepal_client=self.sepal_client,
        )

        results = cs.read_from_csv(result_file)
        msg.set_state("success")

        # Write the results on a comma separated values file, or an excel file

        self.alert.append_msg("Exporting tables...")

        cs.export_reports(
            results,
            reporting_years_sub_a,
            sub_b_year,
            geo_area_name,
            ref_area,
            source_detail,
            transition_matrix,
            report_folder,
            session_id,
            sepal_client=self.sepal_client,
        )

        self.alert.append_msg(
            f"Reporting tables successfull exported {report_folder}", type_="success"
        )
