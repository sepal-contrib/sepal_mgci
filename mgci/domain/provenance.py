"""Stable identities describe scientific dependencies, not widget lifetimes."""

from dataclasses import asdict
from hashlib import sha256
import json

from .configuration import Configuration
from .validation import PURPOSES


def scientific_identity(config: Configuration, indicator: str, purpose: str) -> str:
    if indicator not in ('a', 'b') or purpose not in PURPOSES:
        raise ValueError('Unknown indicator or purpose')
    selected = getattr(config, indicator)
    values = {
        'schema': 1, 'algorithm': config.algorithm_version,
        'aoi': config.aoi_identity, 'aoi_graph': config.aoi_graph, 'workflow': config.workflow,
        'indicator': indicator, 'configuration': asdict(selected),
        'scale': asdict(config.scale), 'biobelt': config.biobelt,
    }
    if indicator == 'b':
        values['transition'] = asdict(config.transition) if config.transition else None
    if purpose in ('statistics', 'chart'):
        if indicator == 'a':
            values['reporting_intervals'] = config.reporting_intervals
        values.update(rsa=config.rsa, dem=config.dem if config.rsa else None, units=config.units)
    encoded = json.dumps(values, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return sha256(encoded.encode()).hexdigest()
