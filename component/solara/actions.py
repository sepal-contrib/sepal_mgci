"""One manual async execution path for statistics, charts, and map preparation."""

import logging
from dataclasses import dataclass
from typing import Callable

import solara
from pysepal.solara.components.task_button import TaskButtonComponent
from pysepal.solara.notifications import use_notifications

from mgci.domain.validation import readiness
from .setup import error_text

log = logging.getLogger('MGCI.solara.actions')


@dataclass(frozen=True)
class RequestRun:
    start: Callable[[], None]
    cancel: Callable[[], None]
    pending: bool


def use_request(state, publish, indicator, purpose, run, *, selection='', prepare=None, on_accept=None):
    """Prepare a request, run it, then accept the result or report the failure.

    ``on_accept`` receives the accepted request; a stale or failed result never reaches it.
    """
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
            log.exception('%s %s failed', indicator.upper(), purpose)
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
                # Success needs no toast: the layer or chart appears.
                if error:
                    notifications.error(error)
                elif on_accept:
                    on_accept(request)

    solara.use_effect(receive, [task.pending, task.cancelled, task.finished, task.error, task.value])

    def cancel():
        if active.current is not None:
            state.cancel(active.current)
        task.cancel()
        publish()

    return RequestRun(start=lambda: task(state.revision(indicator, purpose)), cancel=cancel, pending=task.pending)


@solara.component
def RequestAction(state, publish, indicator, purpose, run, *, label, selection='', prepare=None, disabled=False, block=False):
    request = use_request(state, publish, indicator, purpose, run, selection=selection, prepare=prepare)
    valid = readiness(state.configuration, indicator, purpose).ready
    TaskButtonComponent(label=label, on_start=request.start, on_cancel=request.cancel, running=request.pending,
                        external_busy=disabled or not valid, small=True, block=block)
