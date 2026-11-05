"""Shared source selection and retained drafts for the land-cover dialog."""

import logging
from dataclasses import replace

from mgci.domain.configuration import Workflow
from mgci.errors import LocalizedError

log = logging.getLogger('MGCI.application.landcover')


def _family(workflow):
    return 'default' if workflow in (Workflow.DEFAULT, Workflow.DEFAULT_EDIT_TRANSITIONS) else 'custom'


class WorkflowDrafts:
    def __init__(self, defaults):
        self.defaults = defaults
        self._drafts = {}

    def select(self, state, workflow):
        current = state.configuration
        if workflow == current.workflow:
            return
        self._drafts[current.workflow] = (current.a, current.b, current.transition)
        saved = self._drafts.get(workflow)
        if _family(workflow) == _family(current.workflow):
            # Same dataset: keep its asset, years and classes; only the mapping or transitions differ.
            a, b, transition = current.a, current.b, saved[2] if saved else self.defaults.transition
            if workflow == Workflow.DEFAULT:
                transition = self.defaults.transition
            elif workflow == Workflow.CUSTOM_CANONICAL:
                a, b = replace(a, mapping=()), replace(b, mapping=())
                transition = self.defaults.transition
            elif workflow == Workflow.CUSTOM_RECLASSIFY:
                same = saved is not None and saved[0].asset == current.a.asset
                a = replace(a, mapping=saved[0].mapping if same else ())
                b = replace(b, mapping=saved[1].mapping if same else ())
                transition = saved[2] if saved else None
        elif saved is not None:
            a, b, transition = saved
        elif workflow in (Workflow.DEFAULT, Workflow.DEFAULT_EDIT_TRANSITIONS):
            a, b, transition = self.defaults.a, self.defaults.b, self.defaults.transition
        elif workflow == Workflow.CUSTOM_CANONICAL:
            a, b = replace(current.a, mapping=()), replace(current.b, mapping=())
            transition = self.defaults.transition
        else:
            a, b, transition = current.a, current.b, None
        # Evidence only certifies the AOI for which discovery was completed.
        def in_scope(selected):
            if selected.evidence and selected.evidence.aoi_identity != current.aoi_identity:
                return replace(selected, evidence=None)
            return selected
        state.edit(replace(current, workflow=workflow, a=in_scope(a), b=in_scope(b), transition=transition))


def select_shared_asset(state, resources, asset):
    if all(getattr(state.configuration, key).asset == asset for key in ('a', 'b')):
        return
    for resource in resources.values():
        resource.begin('')
    values = {key: replace(getattr(state.configuration, key), asset=asset,
                           evidence=None, images=(), mapping=()) for key in ('a', 'b')}
    state.edit(replace(state.configuration, **values))


async def inspect_shared_dataset(state, resources, load):
    config = state.configuration
    tokens = {key: resources[key].begin(config.a.asset) for key in ('a', 'b')}
    state.edit(replace(config, a=replace(config.a, evidence=None), b=replace(config.b, evidence=None)))
    captured = state.configuration
    if not captured.a.asset:
        return False
    try:
        result = await load(captured, 'a')
        evidence = result.evidence
        if (evidence.asset != captured.a.asset or evidence.aoi_identity != captured.aoi_identity
                or evidence.status != 'ready' or not evidence.classes or not result.images
                or tuple(image.asset for image in result.images) != evidence.images):
            raise LocalizedError('no_class_evidence')
        # Discovery reads the asset over the area; unrelated edits such as a
        # transition cell do not make it stale.
        current = state.configuration
        if (current.aoi_identity != captured.aoi_identity
                or any(getattr(current, key).asset != captured.a.asset for key in ('a', 'b'))):
            raise LocalizedError('setup_changed_discovery')
    except Exception as error:
        log.warning('Class discovery failed for %s', captured.a.asset, exc_info=True)
        for key in ('a', 'b'):
            resources[key].fail(tokens[key], str(error))
        return False
    accepted = [resources[key].succeed(tokens[key], result) for key in ('a', 'b')]
    if not all(accepted):
        return False
    values = {}
    for key in ('a', 'b'):
        selected = getattr(state.configuration, key)
        retained = tuple(image for image in selected.images if image.asset in evidence.images)
        preferred = tuple(image for image in result.images if image.year in (2000, 2015, 2018))
        images = retained or (preferred if len(preferred) >= 3 else result.images[:3])
        values[key] = replace(selected, evidence=evidence, images=images)
    state.edit(replace(state.configuration, **values))
    log.info('Discovered %d classes and %d images in %s', len(evidence.classes), len(result.images), captured.a.asset)
    return True


def restore_setup(config, snapshot):
    """The configuration after the setup dialog closes unconfirmed: its edits undone.

    The asset, mapping, targets, labels and transitions return to ``snapshot``.
    Classes discovered for an unchanged asset stay: they describe the data, not a choice.
    """
    def restore(current, previous):
        if current.asset != previous.asset:
            return previous
        return replace(current, mapping=previous.mapping, targets=previous.targets, labels=previous.labels)

    return replace(config, a=restore(config.a, snapshot.a), b=restore(config.b, snapshot.b),
                   transition=snapshot.transition)
