"""Explicit dataset selection and inspection, independent of UI and Earth Engine."""

import logging
from dataclasses import replace

from mgci.domain.configuration import DatasetDiscovery
from .state import ResourceState, SessionState

log = logging.getLogger('MGCI.application.discovery')


def select_asset(state: SessionState, indicator: str, asset: str):
    selected = getattr(state.configuration, indicator)
    if asset != selected.asset:
        state.edit(replace(state.configuration, **{
            indicator: replace(selected, asset=asset, evidence=None, images=(), mapping=()),
        }))


async def inspect_dataset(state: SessionState, resource: ResourceState, load, indicator: str) -> bool:
    selected = getattr(state.configuration, indicator)
    token = resource.begin(selected.asset)
    state.edit(replace(state.configuration, **{indicator: replace(selected, evidence=None)}))
    captured = state.configuration
    revision = state.revision(indicator, 'setup')
    if not selected.asset:
        return False
    try:
        result: DatasetDiscovery = await load(captured, indicator)
        evidence = result.evidence
        if (evidence.asset != selected.asset or evidence.aoi_identity != captured.aoi_identity
                or evidence.status != 'ready' or not evidence.classes or not result.images
                or tuple(image.asset for image in result.images) != evidence.images):
            raise ValueError('No complete class evidence for the selected dataset and area')
    except Exception as error:
        log.warning('Class discovery failed for %s', selected.asset, exc_info=True)
        resource.fail(token, str(error))
        return False
    if state.revision(indicator, 'setup') != revision:
        resource.fail(token, 'Setup changed during discovery; get classes again')
        return False
    if not resource.succeed(token, result):
        return False
    current = getattr(state.configuration, indicator)
    retained = tuple(image for image in current.images if image.asset in evidence.images)
    preferred = tuple(image for image in result.images if image.year in (2000, 2015, 2018))
    images = retained or (preferred if len(preferred) >= 3 else result.images[:3])
    state.edit(replace(state.configuration, **{indicator: replace(current, evidence=evidence, images=images)}))
    return True
