from typing import Tuple, Union
from component.types import ResultsDict, SubAYearDict, SubBYearDict

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
    test_time_out: bool = False,
) -> Union[ResultsDict, ee.FeatureCollection, None]:
    if not aoi:
        raise Exception(cm.error.no_aoi)

    if not logger:
        logger = Logger()

    results: ResultsDict = {}
    tasks = {}
    all_succeeded = True

    for year in years:
        process_id = cs.years_from_dict(year)
        logger.set_msg(f"Calculating {process_id}...", id_=process_id)

        matrix = remap_matrix_a if len(years) == 1 else remap_matrix_b

        process = reduce_regions(aoi, matrix, rsa, dem, year, transition_matrix, scale)

        tasks[process_id] = ee.Feature(None, process).set("process_id", process_id)

        if not background:
            try:
                if test_time_out:
                    raise Exception("Computation timed out.")

                result: Union[SubAYearDict, SubBYearDict] = process.getInfo()
                logger.set_msg(f"Calculating {process_id}... Done.", id_=process_id)
                logger.set_state("success", id_=process_id)
                results[process_id] = result
            except Exception as e:
                if "Computation timed out." in str(e):
                    logger.set_msg(
                        f"Warning: {process_id} failed on the fly, it will be processed on the background.",
                        id_=process_id,
                    )
                    logger.set_state("warning", id_=process_id)
                else:
                    # For other exceptions, raise an error
                    raise Exception(f"There was an error trying to compute {e}")

                all_succeeded = False
        else:
            all_succeeded = False
            logger.set_msg(
                f"{process_id} has been scheduled for background processing.",
                id_=process_id,
            )
            logger.set_state("info", id_=process_id)

    if all_succeeded:
        return results
    else:
        # At least one computation failed or background is True
        return ee.FeatureCollection(list(tasks.values()))
