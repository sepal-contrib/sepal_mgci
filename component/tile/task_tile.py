import json
from pathlib import Path

import ipyvuetify as v
import pandas as pd
import sepal_ui.scripts.utils as su
import sepal_ui.sepalwidgets as sw
import component.parameter.directory as DIR
import component.scripts as cs
from component.scripts.gdrive import GDrive
import component.widget as cw
from component.message import cm


class TaskTile(v.Layout, sw.SepalWidget):
    def __init__(self, *args, **kwargs):
        self.class_ = "d-block"
        self._metadata = {"mount_id": "task_tile"}

        super().__init__(*args, **kwargs)

        self.download_task_view = DownloadTaskView()

        self.children = [
            cw.Tabs(
                titles=[
                    "Export from Task",
                ],
                content=[self.download_task_view],
                class_="mb-2",
            ),
        ]


class DownloadTaskView(v.Card):
    def __init__(self, *args, **kwargs):
        """
        Download tile tab: to search and select the tasks_id file, check if the task is
        complete and then download the file.

        """
        self.class_ = "pa-2"

        super().__init__(*args, **kwargs)

        # Widgets
        title = v.CardTitle(children=[cm.dashboard.tasks.title])
        description = v.CardText(
            children=[sw.Markdown(cm.dashboard.tasks.description.format(DIR.TASKS_DIR))]
        )

        v.Icon(children=["mdi-help-circle"], small=True)

        self.w_file_input = sw.FileInput(
            folder=DIR.TASKS_DIR, extensions=[".json"], root=DIR.RESULTS_DIR
        )

        self.alert = sw.Alert()

        self.btn = sw.Btn(cm.dashboard.label.calculate_from_task)

        self.children = [
            title,
            description,
            self.alert,
            self.w_file_input,
            self.btn,
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

        if not tasks_file:
            raise Exception("Select a task file.")

        tasks_file = Path(tasks_file)

        if not tasks_file.exists():
            raise Exception("You have to download and select a task file.")

        with tasks_file.open() as f:
            data = json.loads(f.read())

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
            session_id = data["model_state"]["session_id"]

        # re-build the filename
        task_filename = f"{tasks_file.stem}.csv"

        # Dowload from file
        msg = cw.TaskMsg(f"Processing {task_filename}..", session_id)
        self.alert.append_msg(msg)

        result_file = GDrive().download_from_task_file(
            task_id, tasks_file, task_filename
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
        )

        self.alert.append_msg(
            f"Reporting tables successfull exported {report_folder}", type_="success"
        )
