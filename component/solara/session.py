"""Publish application changes to every mounted state consumer."""

import solara

from mgci.application.state import SessionState
from mgci.domain.configuration import Configuration


class ReactiveSession(SessionState):
    """Keep Solara subscriptions at the presentation boundary.

    Nested MapApp components may retain identical props across parent renders.
    Reading state must subscribe the actual consumer, not just the app shell.
    """

    def __init__(self, initial, publication):
        super().__init__(initial)
        self._publication = publication

    @property
    def configuration(self):
        self._publication.value
        return super().configuration

    @property
    def history(self):
        self._publication.value
        return super().history

    def current(self, indicator, purpose, selection=''):
        self._publication.value
        return super().current(indicator, purpose, selection)

    def revision(self, indicator, purpose):
        self._publication.value
        return super().revision(indicator, purpose)


def use_session_state(initial: Configuration):
    publication = solara.use_reactive(0)
    state = solara.use_memo(lambda: ReactiveSession(initial, publication), [])

    def publish():
        publication.set(publication.value + 1)

    def lifetime():
        return state.close

    solara.use_effect(lifetime, [])
    return state, publish
