"""Module file I/O on SEPAL goes through the client's ``files`` API."""

import asyncio
import json
from io import BytesIO
from pathlib import Path, PurePosixPath

import pandas as pd
import pytest
from eeclient.tasks import Task

import component.parameter.directory as directory
import component.parameter.module_parameter as param
import component.scripts.deferred_calculation as deferred_calculation
import component.scripts.file_handler as file_handler
import component.scripts.gdrive as gdrive
from component.scripts.scripts import create_folder
from tests.fake_sepal import fake_sepal_client

ROOT = "module_results/sdg_indicators/15.4.2"


@pytest.fixture
def sepal():
    return fake_sepal_client()


@pytest.fixture
def remote_dirs(monkeypatch):
    """Result folders as the SEPAL deployment lays them out: relative to the user's home."""
    dirs = directory.Dirs(PurePosixPath(""))
    monkeypatch.setattr(directory, "dir_", dirs)
    monkeypatch.setattr(gdrive, "dir_", dirs)
    return dirs


@pytest.fixture
def current_client(sepal, monkeypatch):
    client, _ = sepal
    monkeypatch.setattr(file_handler, "get_current_sepal_client", lambda: client)
    return client


def ee_task(state):
    return Task.model_validate(
        {
            "name": "projects/p/operations/ABC123",
            "metadata": {
                "@type": "type.googleapis.com/google.earthengine.v1alpha.OperationMetadata",
                "state": state,
                "description": "Task_x",
                "priority": 100,
                "createTime": "2026-09-21T10:00:00Z",
                "type": "EXPORT_FEATURES",
            },
        }
    )


class FakeGEEInterface:
    """Earth Engine is external: answer the two task calls the module makes."""

    def __init__(self, task):
        self.task = task

    async def get_task_async(self, task_id):
        return self.task

    async def export_table_to_drive_async(self, **kwargs):
        return self.task


class RecordingDrive:
    def __init__(self):
        self.downloads = []

    def download_file(self, filename, output_file, sepal_client=None):
        self.downloads.append((filename, output_file, sepal_client))


def test_initialize_remote_creates_the_result_folders(sepal, remote_dirs):
    client, server = sepal

    directory.initialize_remote(client)

    assert server.folders == {
        ROOT,
        f"{ROOT}/custom_classifications",
        f"{ROOT}/custom_map_matrix",
        f"{ROOT}/custom_transition",
        f"{ROOT}/reports",
        f"{ROOT}/tasks",
    }


def test_initialize_remote_uploads_the_default_tables(sepal, remote_dirs):
    client, server = sepal
    defaults = {
        f"{ROOT}/custom_classifications/default_lc_classification.csv": param.LC_CLASSES,
        f"{ROOT}/custom_map_matrix/default_lc_map_matrix.csv": param.LC_MAP_MATRIX,
        f"{ROOT}/custom_transition/transition_matrix.csv": param.TRANSITION_MATRIX_FILE,
    }

    directory.initialize_remote(client)

    assert server.files.keys() == defaults.keys()
    for remote, package_file in defaults.items():
        pd.testing.assert_frame_equal(
            pd.read_csv(BytesIO(server.files[remote])), pd.read_csv(package_file)
        )


def test_initialize_remote_runs_again_for_the_next_session(sepal, remote_dirs):
    client, _ = sepal

    directory.initialize_remote(client)
    directory.initialize_remote(client)


def test_create_folder_creates_it_on_sepal(sepal):
    client, server = sepal

    folder = create_folder(
        PurePosixPath(f"{ROOT}/reports/SDG1542_x"), sepal_client=client
    )

    assert folder == PurePosixPath(f"{ROOT}/reports/SDG1542_x")
    assert f"{ROOT}/reports/SDG1542_x" in server.folders


def test_read_file_reads_a_csv_from_sepal(sepal, current_client):
    _, server = sepal
    server.files[
        f"{ROOT}/custom_classifications/mine.csv"
    ] = b"code,desc\n1,forest\n2,grass\n"

    df = file_handler.read_file(f"{ROOT}/custom_classifications/mine.csv")

    pd.testing.assert_frame_equal(
        df, pd.DataFrame({"code": [1, 2], "desc": ["forest", "grass"]})
    )


def test_df_to_csv_uploads_to_sepal(sepal, current_client):
    _, server = sepal
    df = pd.DataFrame({"code": [1, 2], "desc": ["forest", "grass"]})

    file_handler.df_to_csv(df, f"{ROOT}/custom_classifications/mine.csv")

    assert server.files[f"{ROOT}/custom_classifications/mine.csv"] == (
        b"code,desc\n1,forest\n2,grass\n"
    )


def test_df_to_csv_replaces_an_existing_file(sepal, current_client):
    _, server = sepal
    path = f"{ROOT}/custom_classifications/mine.csv"
    file_handler.df_to_csv(pd.DataFrame({"code": [1]}), path)

    file_handler.df_to_csv(pd.DataFrame({"code": [2]}), path)

    assert server.files[path] == b"code\n2\n"


def test_task_process_uploads_the_task_file(sepal):
    client, server = sepal

    asyncio.run(
        deferred_calculation.task_process(
            process=None,
            task_filepath=Path(f"{ROOT}/tasks/Task_x"),
            model_state={"session_id": "s1"},
            sepal_client=client,
            gee_interface=FakeGEEInterface(ee_task("PENDING")),
        )
    )

    assert json.loads(server.files[f"{ROOT}/tasks/Task_x.json"]) == {
        "model_state": {"session_id": "s1"},
        "task": {"id": "ABC123", "name": "Task_x"},
    }


def test_download_from_task_file_fetches_a_finished_task_into_sepal(sepal, remote_dirs):
    client, server = sepal
    drive = RecordingDrive()

    result = asyncio.run(
        gdrive.download_from_task_file(
            "ABC123",
            Path(f"{ROOT}/tasks/Task_x.json"),
            "Task_x.csv",
            drive_interface=drive,
            gee_interface=FakeGEEInterface(ee_task("SUCCEEDED")),
            sepal_client=client,
        )
    )

    assert result == PurePosixPath(f"{ROOT}/tasks/Task_x/Task_x.csv")
    assert f"{ROOT}/tasks/Task_x" in server.folders
    assert drive.downloads == [("Task_x.csv", result, client)]


def test_download_from_task_file_names_a_task_earth_engine_does_not_know(
    sepal, remote_dirs
):
    client, _ = sepal

    with pytest.raises(Exception, match="Task_x"):
        asyncio.run(
            gdrive.download_from_task_file(
                "UNKNOWN",
                Path(f"{ROOT}/tasks/Task_x.json"),
                "Task_x.csv",
                drive_interface=RecordingDrive(),
                gee_interface=FakeGEEInterface(None),
                sepal_client=client,
            )
        )
