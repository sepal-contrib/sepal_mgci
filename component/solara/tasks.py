"""Explicit background submission and historical result retrieval."""

import logging
import asyncio
from uuid import uuid4

import reacton.ipyvuetify as rv
import solara
from pysepal.solara.components.inputs import FileInputComponent
from pysepal.solara.notifications import use_notifications
from pysepal.solara.components.task_button import TaskButtonComponent
from component.message import msg

from mgci.infrastructure.reports import build_workbook, build_historical_workbook
from mgci.infrastructure.transitions import load_transition
from mgci.infrastructure.tasks import retrieve, TASK_FOLDER
from .toasts import LASTING

log = logging.getLogger('MGCI.solara.tasks')


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
                    return revision, (None, msg('tasks.historical'), payload, None)
                matrix = await load_transition(workspace, original) if original else None
                content = await asyncio.to_thread(build_historical_workbook, payload, record['model_state'], matrix)
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
            output, error, historical, content = result
            if historical is not None:
                needs_transition.set(needs_transition.value or content is None)
            if historical is not None:
                notifications.warning(error)
            elif error:
                notifications.error(error)
            else:
                notifications.success(msg('reports.saved', path=output), timeout=LASTING)
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
        # The button stays enabled and explains a missing file.
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
    # Flat card with the task title, description and file picker.
    with rv.Card(elevation=0, class_='ma-0 pa-0'):
        rv.CardTitle(children=[msg('dashboard.tasks.title')], class_='px-0 mx-0')
        solara.Markdown(msg('dashboard.tasks.description', folder=TASK_FOLDER))
        if sepal_client is not None:
            FileInputComponent(value=path.value, on_value=choose_path, sepal_client=sepal_client,
                               initial_folder=TASK_FOLDER, extensions=['.json'])
        else:
            rv.Alert(type='warning', children=[msg('setup.workspace_required')])
        with rv.Html(tag='div', class_='d-flex justify-end'):
            TaskButtonComponent(label=msg('dashboard.label.calculate_from_task'),
                                on_start=start, on_cancel=cancel, small=True,
                                running=fetch.pending, external_busy=workspace is None)
        if missing.value:
            rv.Alert(type='error', text=True, class_='mt-5', children=[msg('tasks.no_file')])
        if needs_transition.value:
            if sepal_client is not None:
                FileInputComponent(value=original_transition.value, on_value=choose_transition, sepal_client=sepal_client,
                                   extensions=['.csv'], label=msg('tasks.original_transition'))
