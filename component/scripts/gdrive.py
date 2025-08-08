from pathlib import Path
from sepal_ui.scripts.warning import SepalWarning
from sepal_ui.scripts.drive_interface import GDriveInterface
from sepal_ui.scripts.gee_interface import GEEInterface

from component.parameter.directory import dir_

import logging

log = logging.getLogger("MGCI.scripts.gdrive")


def download_from_task_file(
    task_id,
    tasks_file,
    task_filename,
    drive_interface: GDriveInterface,
    gee_interface: GEEInterface,
    sepal_client=None,
):
    """Download csv file result from GDrive

    Args:
        task_id (str): id of the task tasked in GEE.
        tasks_file (Path): path file containing all task_id, task_name
        task_filename (str): name of the task file to be downloaded.
    """

    # Check if the task is completed
    task = gee_interface.get_task(task_id.strip())

    log.debug(f"Task {task_id} state: {task}")

    if task.metadata.state in ["COMPLETED", "SUCCEEDED"]:
        tmp_result_folder = Path(dir_.tasks_dir, Path(tasks_file.name).stem)
        if sepal_client:
            tmp_result_folder = sepal_client.get_remote_dir(tmp_result_folder)
        else:
            tmp_result_folder.mkdir(exist_ok=True)

        tmp_result_file = tmp_result_folder / task_filename
        drive_interface.download_file(task_filename, tmp_result_file, sepal_client)

        log.debug(f"Task path: {tmp_result_file}")

        return tmp_result_file

    elif task.metadata.state == "FAILED":
        raise Exception(f"The task {Path(task_filename).stem} failed.")

    else:
        raise SepalWarning(
            f"The task '{Path(task_filename).stem}' state is: {task.metadata.state}."
        )
