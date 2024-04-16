from typing import Tuple
import ee
from pathlib import Path
import component.parameter.directory as DIR


import component.scripts as cs
from component.scripts.gee import reduce_regions
import component.widget as cw
from component.message import cm
import json


class Logger:
    state = "info"

    def set_msg(self, msg: str, id_: str = None):
        print(self.state, ": ", msg)

    def set_state(self, state: str, id_: str = None):
        self.state = state


def task_process(
    process: ee.FeatureCollection, task_filepath: str, model_state: dict
) -> None:
    """Send the task to the GEE servers and process it in background. This will be
    neccessary when the process is timed out.

    It will return a file with the task name and the task id to track when the process is done.
    Also, it will return the current state of the model to a json file.
    """

    task_name = Path(f"{task_filepath.stem}")

    task = ee.batch.Export.table.toDrive(
        **{
            "collection": process,
            "description": str(task_name),
            "fileFormat": "CSV",
            "selectors": [
                "process_id",
                "sub_a",
                "baseline_degradation",
                "final_degradation",
                "baseline_transition",
                "report_transition",
            ],
        }
    )

    task.start()

    with Path(task_filepath.with_suffix(".json")).open("w") as f:

        data = {
            "model_state": model_state,
            "task": {"id": task.id, "name": str(task_name)},
        }
        print(data)
        json.dump(data, f, indent=4)


def perform_calculation(
    aoi: ee.Geometry,
    rsa: bool,
    dem: str,
    remap_matrix_a: dict,
    remap_matrix_b: dict,
    transition_matrix: str,
    years: list,
    logger: cw.Alert = None,
    background: bool = False,
    scale: int = None,
):
    if not aoi:
        raise Exception(cm.error.no_aoi)

    if not logger:
        logger = Logger()

    class Fly:
        def __init__(self):
            self.on_the_fly = True

        def set(self, value):
            self.on_the_fly = value

        def get(self):
            return self.on_the_fly

    on_the_fly = Fly()
    on_the_fly.set(not background)

    def calculation(years: Tuple, on_the_fly: bool):
        """perform the computation on the fly or fallback to gee background

        args:
            year (list(list)) : list of year list to perform calculation
            task_filename: name of the task file (result ids will be append to the file)
        """
        process_id = cs.years_from_dict(years)
        logger.set_msg(f"Calculating {process_id}...", id_=process_id)

        matrix = remap_matrix_a if len(years) == 1 else remap_matrix_b
        process = reduce_regions(aoi, matrix, rsa, dem, years, transition_matrix, scale)

        if on_the_fly.get():

            # Try the process in on the fly
            try:
                result = process.getInfo()
                logger.set_msg(f"Calculating {process_id}... Done.", id_=process_id)
                logger.set_state("success", id_=process_id)
                on_the_fly.set(True)

                return result

            except Exception as e:
                if e.args[0] == "Computation timed out.":
                    # Create an unique name (to search after in Drive)
                    logger.set_msg(
                        f"Warning: {process_id} failed on the fly.", id_=process_id
                    )
                    logger.set_state("warning", id_=process_id)
                    on_the_fly.set(False)

                    return ee.Feature(None, process).set("process_id", process_id)

                else:
                    raise Exception(f"There was an error trying to compute {e}")

        else:
            logger.set_msg(
                f"Warning: {process_id} has been tasked on GEE background.",
                id_=process_id,
            )
            logger.set_state("warning", id_=process_id)
            return ee.Feature(None, process).set("process_id", process_id)

    results = {}
    for year in years:
        results[cs.years_from_dict(year)] = calculation(year, on_the_fly)

    if not on_the_fly.get():
        # If the process was not done on the fly, send it to the GEE servers
        # but first merge all the processes in one.
        return False, ee.FeatureCollection(list(results.values()))

    return True, results
