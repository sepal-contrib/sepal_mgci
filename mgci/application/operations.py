"""Explicit setup operations with injected external work."""

import logging
from dataclasses import replace

from .state import ResourceState, SessionState
from mgci.errors import LocalizedError

log = logging.getLogger('MGCI.application.operations')


async def select_transition(state: SessionState, resource: ResourceState, load, path: str, *, refresh=False) -> bool:
    """Select/refresh a file; the injected loader returns an immutable table."""
    token = resource.begin(path)
    if not refresh:
        state.edit(replace(state.configuration, transition=None))
    revision = state.revision('b', 'statistics')
    if not path:
        return False
    try:
        table = await load(path)
    except Exception as error:
        log.warning('Could not read transition file %s', path, exc_info=True)
        if resource.fail(token, str(error)) and state.revision('b', 'statistics') == revision:
            state.edit(replace(state.configuration, transition=None))
        return False
    if state.revision('b', 'statistics') != revision:
        resource.fail(token, LocalizedError('setup_changed_loading'))
        return False
    if not resource.succeed(token, table):
        return False
    state.edit(replace(state.configuration, transition=table))
    return True


async def refresh_transition(state: SessionState, load) -> bool:
    """Re-read an explicitly selected matrix so content changes at the same path count.

    A failed read raises and leaves the configuration, and so the current B outputs,
    unchanged; the file picker's resource is not involved.
    """
    table = state.configuration.transition
    if table is None or not table.explicitly_selected:
        return table is not None
    revision = state.revision('b', 'statistics')
    log.debug('Refreshing transition file %s', table.source)
    fresh = await load(table.source)
    if state.revision('b', 'statistics') != revision or state.configuration.transition != table:
        raise LocalizedError('settings_changed')
    if fresh != table:
        state.edit(replace(state.configuration, transition=fresh))
    return True


async def prepare_request(state, indicator, purpose, selection='', *, load=None):
    """Refresh an explicitly selected B matrix before capturing execution inputs."""
    if indicator == 'b' and state.configuration.transition and state.configuration.transition.explicitly_selected:
        if load is None:
            raise ValueError('A workspace loader is required to refresh the selected transition file')
        await refresh_transition(state, load)
    return state.prepare(indicator, purpose, selection)
