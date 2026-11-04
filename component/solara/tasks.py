"""Explicit background submission and historical result retrieval."""

import logging
import asyncio
from pathlib import PurePosixPath
from uuid import uuid4

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.inputs import FileInputComponent
from pysepal.solara.notifications import use_notifications
from pysepal.solara.components.task_button import TaskButtonComponent
from component.message import cm

from mgci.domain.validation import readiness
from mgci.infrastructure.reports import build_workbook, build_legacy_workbook
from mgci.infrastructure.transitions import load_transition
from mgci.infrastructure.tasks import submit, retrieve, TASK_FOLDER
from .messages import msg

log = logging.getLogger('MGCI.solara.tasks')


@solara.component
def BackgroundAction(state, publish, indicator, gee_interface, workspace, prepare):
    notifications = use_notifications()

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def run(revision):
        request = None
        if state.revision(indicator, 'statistics') != revision:
            return None
        try:
            request = await prepare(indicator, 'statistics', '')
            record, path = await submit(request, gee_interface, workspace)
            return path, None
        except Exception as error:
            log.exception('Background calculation of %s failed', indicator.upper())
            if request:
                state.fail(request, str(error))
            return None, str(error)
        finally:
            publish()

    def receive():
        if run.finished and run.value:
            path, error = run.value
            notifications.error(error) if error else notifications.success(msg('tasks.submitted', path=path))
    solara.use_effect(receive, [run.finished, run.value])
    TaskButtonComponent(label=msg('tasks.submit', indicator=indicator.upper()), small=True, running=run.pending,
                        external_busy=workspace is None or not readiness(state.configuration, indicator, 'statistics').ready,
                        on_start=lambda: run(state.revision(indicator, 'statistics')), on_cancel=run.cancel)


@solara.component
def TaskPanel(state, publish, workspace, gee_interface, drive_interface, sepal_client):
    path = solara.use_reactive('')
    original_transition = solara.use_reactive('')
    notifications = use_notifications()
    generation = solara.use_ref(0)
    completed = solara.use_reactive(None)
    needs_transition = solara.use_reactive(False)
    missing = solara.use_reactive(False)

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def fetch(revision, selected, original):
        try:
            request, payload, record = await retrieve(selected, workspace, gee_interface, drive_interface)
            if revision != generation.current:
                return None
            if request is None:
                if any('_' in key for key in payload) and not original:
                    return revision, (None, msg('tasks.legacy'), payload, None)
                matrix = await load_transition(workspace, original) if original else None
                content = await asyncio.to_thread(build_legacy_workbook, payload, record['model_state'], matrix)
                identifier = str(uuid4())
            else:
                from mgci.application.state import Artifact, freeze_payload
                artifact = Artifact(request, freeze_payload(payload))
                content = await asyncio.to_thread(build_workbook, (artifact,))
                identifier = str(uuid4())
            if revision != generation.current:
                return None
            folder = 'module_results/sdg_indicators/15.4.2/reports'
            output = f'{folder}/SDG1542_{identifier}.xlsx'
            await workspace.mkdir_async(folder, parents=True)
            if revision != generation.current:
                return None
            await workspace.write_async(output, content)
            log.info('Task report saved to %s', output)
            if revision != generation.current:
                return None
            if request is not None:
                state.complete_background(request, payload)
                publish()
            result = (output, msg('tasks.historical_saved', path=output), payload, content) if request is None else (output, None, None, content)
            return revision, result
        except Exception as error:
            log.exception('Task retrieval failed')
            return revision, (None, str(error), None, None)

    def receive():
        if fetch.finished and fetch.value:
            revision, result = fetch.value
            if revision != generation.current:
                return
            completed.set(result)
            output, error, legacy, content = result
            if legacy is not None:
                needs_transition.set(needs_transition.value or content is None)
            if legacy is not None:
                notifications.warning(error)
            elif error:
                notifications.error(error)
            else:
                notifications.success(msg('reports.saved', path=output))
    solara.use_effect(receive, [fetch.pending, fetch.finished, fetch.error, fetch.cancelled, fetch.value])

    def cancel():
        generation.current += 1
        if fetch.pending:
            fetch.cancel()

    def choose_path(value):
        cancel()
        missing.set(False)
        path.set(value or '')
        original_transition.set('')
        completed.set(None)
        needs_transition.set(False)

    def choose_transition(value):
        cancel()
        original_transition.set(value or '')
        completed.set(None)

    def start():
        # Like the legacy tile, the button stays enabled and explains a missing file.
        if not path.value:
            missing.set(True)
            return
        missing.set(False)
        generation.current += 1
        completed.set(None)
        fetch(generation.current, path.value, original_transition.value)

    def lifetime():
        return cancel
    solara.use_effect(lifetime, [])
    # Legacy DownloadTaskView: flat card, catalogue title/description, default file button.
    with rv.Card(elevation=0, class_='ma-0 pa-0'):
        rv.CardTitle(children=[cm.dashboard.tasks.title], class_='px-0 mx-0')
        solara.Markdown(cm.dashboard.tasks.description.format(TASK_FOLDER))
        if sepal_client is not None:
            FileInputComponent(value=path.value, on_value=choose_path, sepal_client=sepal_client,
                               initial_folder=TASK_FOLDER, extensions=['.json'])
        else:
            rv.Alert(type='warning', children=[msg('setup.workspace_required')])
        TaskButtonComponent(label=cm.dashboard.label.calculate_from_task,
                            on_start=start, on_cancel=cancel, small=True,
                            running=fetch.pending, external_busy=workspace is None)
        if missing.value:
            rv.Alert(type='error', text=True, class_='mt-5', children=[msg('tasks.no_file')])
        if completed.value and completed.value[3] is not None:
            solara.FileDownload(completed.value[3], filename=PurePosixPath(completed.value[0]).name,
                                label=msg('task_report.download'))
        if needs_transition.value:
            if sepal_client is not None:
                FileInputComponent(value=original_transition.value, on_value=choose_transition, sepal_client=sepal_client,
                                   extensions=['.csv'], label=msg('tasks.original_transition'))
        if completed.value and completed.value[2] is not None:
            import json
            solara.FileDownload(json.dumps(completed.value[2], indent=2).encode(), filename='historical-results.json', label=msg('tasks.download'))
