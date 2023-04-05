import concurrent.futures
from pathlib import Path
from time import sleep

import ipyvuetify as v
import sepal_ui.scripts.utils as su
import sepal_ui.sepalwidgets as sw
from traitlets import link

import component.parameter.directory as DIR
import component.parameter.module_parameter as param
import component.scripts as cs
import component.widget as cw
from component.message import cm

__all__ = ["CalculationTile"]


class CalculationTile(v.Layout, sw.SepalWidget):
    def __init__(self, model, *args, **kwargs):
        self.class_ = "d-block"
        self._metadata = {"mount_id": "calculation_tile"}

        super().__init__(*args, **kwargs)

        self.model = model

        self.calculation_view = CalculationView(self.model)
        self.download_task_view = DownloadTaskView(self.model)

        self.children = [
            cw.Tabs(
                titles=[
                    "Calculation",
                    "Calculation from Task",
                ],
                content=[
                    self.calculation_view,
                    self.download_task_view,
                ],
                class_="mb-2",
            ),
        ]


class CalculationView(sw.Card):
    def __init__(self, model, rsa=False, *args, **kwargs):
        """Dashboard tile to calculate and resume the zonal statistics for the
        vegetation layer by kapos ranges.

        Args:
            model (MgciModel): Mgci Model

        """

        self.class_ = "pa-2"
        self.attributes = {"id": "calculation_view"}

        super().__init__(*args, **kwargs)

        self.model = model
        self.calculation = cw.Calculation(self.model)

        title = v.CardTitle(children=[cm.dashboard.title])
        description = v.CardText(children=[cm.dashboard.description])

        v.Icon(children=["mdi-help-circle"], small=True)

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
    def run_statistics(self, *args):
        """Start the calculation of the statistics. It will start the process on the fly
        or making a task in the background depending if the rsa is selected or if the
        computation is taking so long."""
        # Clear previous loaded results

        area_type = (
            cm.dashboard.label.rsa_name
            if self.w_use_rsa.v_model
            else cm.dashboard.label.plan
        )

        if not any([self.model.calc_a, self.model.calc_b]):
            raise Exception(cm.calculation.error.no_subind)
        else:
            if all([not self.model.sub_a_year, not self.model.sub_b_year]):
                raise Exception(cm.calculation.error.no_years)

        # TODO: Check that user years are consistent:
        # - for sub_b: there cannot be repeated reporting years
        # - for sub_a: check that reporting is higher than baseline

        # TODO: assert that sub_a_matrix only have 10 classes

        # Calculate regions

        head_msg = sw.Flex(children=[cm.dashboard.alert.computing.format(area_type)])

        self.alert.add_msg(head_msg)

        def deferred_calculation(year, task_filename):
            """perform the computation on the fly or fallback to gee background

            args:
                year (list(list)) : list of year list to perform calculation
                task_filename: name of the task file (result ids will be append to the file)
            """
            print(year)
            process_id = cs.years_from_dict(year)
            msg = cw.TaskMsg(f"Calculating {process_id}..")
            self.alert.append_msg(msg)

            start_year = year[0].get("asset")

            if len(year) > 1:

                end_year = year[1].get("asset")
                process = self.model.reduce_to_regions("sub_b", start_year, end_year)

            else:
                process = self.model.reduce_to_regions("sub_a", start_year)

            # Try the process in on the fly
            try:
                result = process.getInfo()
                msg.set_msg(f"Calculating {process_id}... Done.")
                msg.set_state("success")

                return result

            except Exception as e:
                if e.args[0] != "Computation timed out.":
                    # Create an unique name (to search after in Drive)
                    self.model.task_process(process, task_filename, process_id)
                    msg.set_msg(f"Calculating {process_id}... Tasked.")
                    msg.set_state("warning")

                else:
                    raise Exception(f"There was an error {e}")

        with concurrent.futures.ThreadPoolExecutor() as executor:

            self.model.done = False

            # set same_year_matrix variable from model, it will be used when quering the
            # dashboard
            self.model.same_asset_matrix = all(
                [
                    self.model.matrix_sub_a,
                    self.model.matrix_sub_b,
                    self.model.lc_asset_sub_a,
                    self.model.lc_asset_sub_b,
                ],
            )

            years = cs.get_years(
                self.model.sub_a_year,
                self.model.sub_b_year,
                self.model.matrix_sub_a,
                self.model.matrix_sub_b,
            )

            unique_preffix = su.random_string(4).upper()

            # Create only one file to store all task ids for the current session.
            task_file = DIR.TASKS_DIR / f"Task_result_{unique_preffix}"

            futures = {
                executor.submit(
                    deferred_calculation, year, task_file
                ): cs.years_from_dict(year)
                for year in years
            }

            self.model.results, results = {}, {}
            # As we don't know which task was completed first, we have to save them in a
            # key(grid_size) : value (future.result()) format
            for future in concurrent.futures.as_completed(futures):
                future_name = futures[future]
                results[future_name] = future.result()

            # If result is None, we assume the computation was tasked

            if not all(results.values()):
                task_filename = task_file.with_suffix(".csv")
                self.alert.append_msg(
                    f"The computation has been tasked {task_filename}.", type_="warning"
                )

            elif all(results.values()):
                self.model.results = results
                self.model.done = True
                self.alert.append_msg(
                    "The computation has been performed.", type_="success"
                )

            else:
                self.alert.append_msg(
                    "There was an error in one of the steps", type_="error"
                )


class DownloadTaskView(v.Card):
    def __init__(self, model, *args, **kwargs):
        """
        Download tile tab: to search and select the tasks_id file, check if the task is
        complete and then download the file.

        """
        self.class_ = "pa-2"

        super().__init__(*args, **kwargs)

        self.model = model

        # Widgets
        title = v.CardTitle(children=[cm.dashboard.tasks.title])
        description = v.CardText(
            children=[sw.Markdown(cm.dashboard.tasks.description.format(DIR.TASKS_DIR))]
        )

        v.Icon(children=["mdi-help-circle"], small=True)

        self.w_file_input = sw.FileInput(folder=DIR.TASKS_DIR, extentions=[".csv"])

        self.alert = sw.Alert()
        self.btn = sw.Btn(cm.dashboard.label.calculate)

        self.children = [title, description, self.w_file_input, self.btn, self.alert]

        self.btn.on_event("click", self.run_statistics)

    @su.loading_button(debug=True)
    def run_statistics(self, widget, event, data):

        # Get and read file
        tasks_file = Path(self.w_file_input.v_model)
        tasks_df = self.model.read_tasks_file(tasks_file)

        def extract_from_tasks_file(tasks_file, process_id, task_id):
            """From the gee result dictionary, extract the values and give a proper
            format in a pd.DataFrame.

            Args:
                process (ee.reduceRegion): ee process (without execution).
                task_file (path, str): full path of task file containing task_id(s)
            """

            # re-build the filename
            task_filename = f"{tasks_file.stem}_{process_id}.csv"

            # Dowload from file
            msg = cw.TaskMsg(f"Calculating {process_id}..")
            self.alert.append_msg(msg)

            result_file = self.model.download_from_task_file(
                task_id, tasks_file, task_filename
            )

            result = cs.read_from_csv(result_file, process_id)
            sleep(0.5)
            msg.set_msg(f"Calculating {process_id}... Done!.")
            msg.set_state("success")

            return result

        with concurrent.futures.ThreadPoolExecutor() as executor:
            self.model.done = False

            futures = {
                executor.submit(
                    extract_from_tasks_file,
                    tasks_file,
                    row.iloc[0].strip(),
                    row.iloc[1].strip(),
                ): row.iloc[0].strip()
                for idx, row in tasks_df.iterrows()
            }

            self.model.results, results = {}, {}

            for future in concurrent.futures.as_completed(futures):
                future_name = futures[future]
                results[future_name] = future.result()

            self.model.results = results
            self.model.done = True
