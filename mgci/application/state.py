"""Single-owner lifecycle; call mutations on the session's UI event loop."""

import logging
from dataclasses import dataclass, replace
from types import MappingProxyType
import random
from uuid import uuid4

from mgci.domain.configuration import Configuration, Workflow
from mgci.domain.provenance import scientific_identity
from mgci.domain.validation import PURPOSES, NotReady, readiness

log = logging.getLogger('MGCI.application.state')


def freeze_payload(value):
    if isinstance(value, dict):
        return MappingProxyType({key: freeze_payload(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(freeze_payload(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError('Adapters must return plain data, not mutable library objects')


@dataclass(frozen=True)
class Request:
    session: str
    request_id: str
    slot: tuple[str, str, str]
    generation: int
    identity: str
    configuration: Configuration


@dataclass(frozen=True)
class Artifact:
    request: Request
    payload: object


@dataclass
class OutputSlot:
    generation: int = 0
    latest: Request | None = None
    artifact: Artifact | None = None
    status: str = 'empty'
    error: str | None = None


class SessionState:
    def __init__(self, configuration: Configuration):
        self._configuration = configuration
        self._session = str(uuid4())
        # Short legacy number in report and export names (SDG1542_<AOI><session_id>).
        self.session_id = random.randint(1000, 9999)
        self._mounted = True
        self._slots = {}
        self._history = []
        self._revisions = {(indicator, purpose): 0 for indicator in ('a', 'b') for purpose in PURPOSES}

    @property
    def configuration(self):
        return self._configuration

    @property
    def history(self):
        return tuple(self._history)

    def edit(self, configuration: Configuration):
        if not self._mounted:
            raise ValueError('Session is closed')
        if (configuration.workflow == Workflow.CUSTOM_RECLASSIFY
                and self._configuration.workflow != configuration.workflow):
            configuration = replace(configuration, transition=None)
        changed = []
        for indicator, purpose in self._revisions:
            if scientific_identity(self._configuration, indicator, purpose) != scientific_identity(configuration, indicator, purpose):
                self._revisions[indicator, purpose] += 1
                changed.append(f'{indicator}/{purpose}')
        if changed:
            log.debug('Edit invalidates %s', ', '.join(changed))
        for (indicator, purpose, _), slot in self._slots.items():
            before = scientific_identity(self._configuration, indicator, purpose)
            after = scientific_identity(configuration, indicator, purpose)
            if before != after:
                slot.generation += 1
                slot.latest = None
                slot.artifact = None
                slot.status = 'empty'
                slot.error = None
        self._configuration = configuration

    def revision(self, indicator: str, purpose: str) -> int:
        return self._revisions[indicator, purpose]

    def prepare(self, indicator: str, purpose: str, selection: str = '') -> Request:
        if not self._mounted:
            raise ValueError('Session is closed')
        validation = readiness(self._configuration, indicator, purpose)
        if not validation.ready:
            raise NotReady(validation.issues)
        key = (indicator, purpose, selection)
        slot = self._slots.setdefault(key, OutputSlot())
        request = Request(self._session, str(uuid4()), key, slot.generation,
                          scientific_identity(self._configuration, indicator, purpose),
                          self._configuration)
        slot.latest, slot.artifact = request, None
        slot.status, slot.error = 'pending', None
        log.debug('Prepared %s %s', '/'.join(filter(None, key)), request.request_id[:8])
        return request

    def _accepts(self, request: Request) -> bool:
        slot = self._slots.get(request.slot)
        return bool(self._mounted and request.session == self._session and slot
                    and slot.latest == request and slot.status == 'pending'
                    and slot.generation == request.generation
                    and request.identity == scientific_identity(
                        self._configuration, request.slot[0], request.slot[1]))

    def accept(self, request: Request, payload) -> bool:
        if not self._accepts(request):
            log.debug('Rejected stale result %s %s', '/'.join(filter(None, request.slot)), request.request_id[:8])
            return False
        log.debug('Accepted %s %s', '/'.join(filter(None, request.slot)), request.request_id[:8])
        artifact = Artifact(request, freeze_payload(payload))
        slot = self._slots[request.slot]
        slot.artifact, slot.status = artifact, 'ready'
        self._history.append(artifact)
        return True

    def complete_background(self, request: Request, payload) -> Artifact:
        for artifact in self._history:
            if artifact.request.request_id == request.request_id:
                if artifact.request != request:
                    raise ValueError('Conflicting task provenance')
                return artifact
        if self.accept(request, payload):
            return self.current(*request.slot)
        artifact = Artifact(request, freeze_payload(payload))
        if self._mounted:
            self._history.append(artifact)
        return artifact

    def fail(self, request: Request, error: str) -> bool:
        if not self._accepts(request):
            return False
        slot = self._slots[request.slot]
        slot.status, slot.error = 'error', str(error)
        log.debug('Failed %s %s: %s', '/'.join(filter(None, request.slot)), request.request_id[:8], error)
        return True

    def cancel(self, request: Request) -> bool:
        if not self._accepts(request):
            return False
        self._slots[request.slot].status = 'cancelled'
        log.debug('Cancelled %s %s', '/'.join(filter(None, request.slot)), request.request_id[:8])
        return True

    def current(self, indicator: str, purpose: str, selection: str = ''):
        slot = self._slots.get((indicator, purpose, selection))
        return slot.artifact if self._mounted and slot else None

    def export_artifact(self, request: Request) -> Artifact:
        artifact = self.current(*request.slot)
        if artifact is None or artifact.request != request:
            raise ValueError('Output is no longer current')
        return artifact

    def close(self):
        self._mounted = False
        for key in self._revisions:
            self._revisions[key] += 1
        self._slots.clear()


@dataclass(frozen=True)
class ResourceToken:
    owner: str
    generation: int
    selection: str


class ResourceState:
    def __init__(self):
        self._owner = str(uuid4())
        self._generation = 0
        self._token = None
        self.status = 'empty'
        self.value = None
        self.error = None

    def begin(self, selection: str) -> ResourceToken:
        self._generation += 1
        self._token = ResourceToken(self._owner, self._generation, selection)
        self.status = 'loading' if selection else 'empty'
        self.value, self.error = None, None
        return self._token

    def succeed(self, token: ResourceToken, value) -> bool:
        if token != self._token or self.status != 'loading':
            return False
        self.value, self.status = value, 'ready'
        return True

    def fail(self, token: ResourceToken, error: str) -> bool:
        if token != self._token or self.status != 'loading':
            return False
        self.error, self.status = str(error), 'error'
        return True
