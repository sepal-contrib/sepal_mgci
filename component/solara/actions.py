"""One manual async execution path for statistics, charts, and map preparation."""

import solara
from pysepal.solara.components.task_button import TaskButtonComponent
from pysepal.solara.notifications import use_notifications

from mgci.domain.validation import readiness
from .messages import msg
from .setup import error_text


@solara.component
def RequestAction(state, publish, indicator, purpose, run, *, label, selection='', prepare=None, disabled=False, block=False):
    notifications = use_notifications()
    active = solara.use_ref(None)

    @solara.lab.use_task(dependencies=None, raise_error=False, prefer_threaded=False)
    async def task(revision):
        request = None
        if state.revision(indicator, purpose) != revision:
            return None
        try:
            request = await prepare(indicator, purpose, selection) if prepare else state.prepare(indicator, purpose, selection)
            active.current = request
            publish()
            return request, await run(request), None, revision
        except Exception as error:
            return request, None, error_text(error), revision

    def receive():
        if task.finished and task.value is not None:
            request, payload, error, revision = task.value
            if request is None:
                if error and state.revision(indicator, purpose) == revision:
                    notifications.error(error)
                return
            accepted = state.fail(request, error) if error else state.accept(request, payload)
            if accepted:
                publish()
                if error:
                    notifications.error(error)
                else:
                    notifications.success(msg('calculation.complete'))

    solara.use_effect(receive, [task.pending, task.cancelled, task.finished, task.error, task.value])

    def cancel():
        if active.current is not None:
            state.cancel(active.current)
        task.cancel()
        publish()

    valid = readiness(state.configuration, indicator, purpose).ready
    TaskButtonComponent(label=label, on_start=lambda: task(state.revision(indicator, purpose)),
                        on_cancel=cancel, running=task.pending, external_busy=disabled or not valid, small=True, block=block)
