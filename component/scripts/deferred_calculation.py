import ee
from pathlib import Path
import concurrent.futures
import component.parameter.directory as DIR


from typing import Tuple
import component.scripts as cs
import sepal_ui.scripts.utils as su
from component.scripts.reduce import reduce_regions
from component.scripts.scripts import map_matrix_to_dict
import component.widget as cw


class Logger:
    state = "info"

    def set_msg(self, msg: str):
        print(self.state, ": ", msg)

    def set_state(self, state: str):
        self.state = state


def task_process(process, task_file, process_id):
    """Send the task to the GEE servers and process it in background. This will be
    neccessary when the process is timed out."""

    task_name = Path(f"{task_file.name}_{process_id}")

    task = ee.batch.Export.table.toDrive(
        **{
            "collection": ee.FeatureCollection([ee.Feature(None, process)]),
            "description": str(task_name),
            "fileFormat": "CSV",
        }
    )

    task.start()

    # Create a file containing the task id to track when the process is done.
    with open(task_file.with_suffix(".csv"), "a") as file:
        file.write(f"{process_id}, {task.id}" + "\n")


def perform_calculation(
    aoi: ee.Geometry,
    rsa: bool,
    dem: str,
    remap_matrix_a: dict,
    remap_matrix_b: dict,
    transition_matrix: str,
    years: list,
    logger: cw.TaskMsg = None,
):
    if not aoi:
        raise Exception("Please select an area of interest")

    if not logger:
        logger = Logger()

    def deferred_calculation(years: Tuple):
        """perform the computation on the fly or fallback to gee background

        args:
            year (list(list)) : list of year list to perform calculation
            task_filename: name of the task file (result ids will be append to the file)
        """
        process_id = cs.years_from_dict(years)
        logger.set_msg(f"Calculating {process_id}...")

        matrix = remap_matrix_a if len(years) == 1 else remap_matrix_b
        process = reduce_regions(aoi, matrix, rsa, dem, years, transition_matrix)

        # Try the process in on the fly
        try:
            result = process.getInfo()
            logger.set_msg(f"Calculating {process_id}... Done.")
            logger.set_state("success")

            return result

        except Exception as e:
            if e.args[0] != "Computation timed out.":
                # Create an unique name (to search after in Drive)
                task_process(process, task_file, process_id)
                logger.set_msg(f"Calculating {process_id}... Tasked.")
                logger.set_state("warning")

            else:
                raise Exception(f"There was an error {e}")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = {}
        unique_preffix = su.random_string(4).upper()
        task_file = DIR.TASKS_DIR / f"Task_result_{unique_preffix}"

        futures = {
            executor.submit(deferred_calculation, year): cs.years_from_dict(year)
            for year in years
        }

        # As we don't know which task was completed first, we have to save them in a
        # key(grid_size) : value (future.result()) format
        for future in concurrent.futures.as_completed(futures):
            future_name = futures[future]
            results[future_name] = future.result()

        return results, task_file
