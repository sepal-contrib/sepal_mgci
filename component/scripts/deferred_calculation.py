import logging
import json
from typing import Union
import asyncio
import ee
from pathlib import Path

from sepal_ui.scripts.gee_interface import GEEInterface

import component.scripts as cs
from component.types import ResultsDict, SubAYearDict, SubBYearDict
from component.scripts.gee import reduce_regions
import component.widget as cw
from component.message import cm


log = logging.getLogger("MGCI.scripts.deferred_calculation")


class Logger:
    state = "info"

    def set_msg(self, msg: str, id_: str = None):
        print(self.state, ": ", msg)

    def set_state(self, state: str, id_: str = None):
        self.state = state


async def task_process(
    process: ee.FeatureCollection,
    task_filepath: str,
    model_state: dict,
    sepal_client=None,
    gee_interface: GEEInterface = None,
) -> None:
    """Send the task to the GEE servers and process it in background. This will be
    neccessary when the process is timed out.

    It will return a file with the task name and the task id to track when the process is done.
    Also, it will return the current state of the model to a json file.
    """

    task_name = Path(f"{task_filepath.stem}")

    task = await gee_interface.export_table_to_drive_async(
        **{
            "collection": process,
            "description": str(task_name),
            "file_format": "CSV",
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

    log.debug(f"Task {task_name} >>>>>>>>>>>>>>: {task}")

    task_path = task_filepath.with_suffix(".json")

    data = {
        "model_state": model_state,
        "task": {"id": task.id, "name": str(task_name)},
    }
    json_data = json.dumps(data, indent=4)

    if sepal_client:
        return sepal_client.set_file(task_path, json_data)
    else:
        # Save the file to the local system
        with Path(task_path).open("w") as f:
            f.write(json_data)

        return Path(task_path)


async def perform_calculation(
    gee_interface: GEEInterface,
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

    # If background processing is requested, skip direct computation
    if background:
        for year in years:
            process_id = cs.years_from_dict(year)
            logger.set_msg(
                f"{process_id} has been scheduled for background processing.",
                id_=process_id,
            )
            logger.set_state("info", id_=process_id)

            matrix = remap_matrix_a if len(years) == 1 else remap_matrix_b
            process = reduce_regions(
                aoi, matrix, rsa, dem, year, transition_matrix, scale
            )
            tasks[process_id] = ee.Feature(None, process).set("process_id", process_id)

        # Add a minimal await to maintain async behavior for callers
        await asyncio.sleep(0.1)
        return ee.FeatureCollection(list(tasks.values()))

    # For non-background processing, create coroutines for all years
    async def process_year(year):
        process_id = cs.years_from_dict(year)
        logger.set_msg(f"Calculating {process_id}...", id_=process_id)

        matrix = remap_matrix_a if len(years) == 1 else remap_matrix_b

        # Call reduce_regions which is now synchronous
        process = reduce_regions(aoi, matrix, rsa, dem, year, transition_matrix, scale)

        if test_time_out:
            raise Exception("Computation timed out.")

        result: Union[SubAYearDict, SubBYearDict] = await gee_interface.get_info_async(
            process, tag=process_id
        )

        logger.set_msg(f"Calculating {process_id}... Done.", id_=process_id)
        logger.set_state("success", id_=process_id)

        return process_id, result, process

    # Create coroutines for all years
    year_coros = [process_year(year) for year in years]

    # Use asyncio.gather to fail fast and handle cancellation properly
    try:
        year_results = await asyncio.gather(*year_coros)

        # If we get here, all tasks succeeded
        for process_id, result_data, process in year_results:
            results[process_id] = result_data
            tasks[process_id] = ee.Feature(None, process).set("process_id", process_id)

    except asyncio.CancelledError:

        # Set cancellation state for all tasks
        for year in years:
            process_id = cs.years_from_dict(year)
            logger.set_msg(f"{process_id} has been cancelled.", id_=process_id)
            logger.set_state("error", id_=process_id)

        logger.type = "error"

        raise
    except Exception as e:
        # At least one task failed, fall back to background processing
        if "Computation timed out." in str(e) or "User memory limit exceeded" in str(e):
            logger.set_msg(
                f"Warning: At least one computation failed on the fly. All tasks will be processed on the background.",
                id_="batch",
            )
            logger.set_state("warning", id_="batch")
        else:
            # For other exceptions, raise an error
            raise Exception(f"There was an error trying to compute: {e}")

        all_succeeded = False

        # Create tasks for all years since we need to process them in background
        tasks = {}
        for year in years:
            process_id = cs.years_from_dict(year)
            matrix = remap_matrix_a if len(years) == 1 else remap_matrix_b
            process = reduce_regions(
                aoi, matrix, rsa, dem, year, transition_matrix, scale
            )
            tasks[process_id] = ee.Feature(None, process).set("process_id", process_id)

    except asyncio.CancelledError:
        # The main function was cancelled, re-raise to propagate cancellation
        raise
    except Exception as e:
        # If gather() itself fails unexpectedly, fall back to background processing
        logger.set_msg(
            f"Warning: Batch processing failed ({e}). Falling back to background processing.",
            id_="batch",
        )
        all_succeeded = False

        # Create tasks for all years
        tasks = {}
        for year in years:
            process_id = cs.years_from_dict(year)
            matrix = remap_matrix_a if len(years) == 1 else remap_matrix_b
            process = reduce_regions(
                aoi, matrix, rsa, dem, year, transition_matrix, scale
            )
            tasks[process_id] = ee.Feature(None, process).set("process_id", process_id)

    if all_succeeded:
        return results
    else:
        # At least one computation failed
        return ee.FeatureCollection(list(tasks.values()))
