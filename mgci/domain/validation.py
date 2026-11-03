"""Readiness is derived from current values, never from a validation flag."""

from dataclasses import dataclass
from itertools import product

from .configuration import Configuration, Workflow
from .reporting import reporting_breakpoints

PURPOSES = frozenset(('setup', 'statistics', 'chart', 'layer', 'image_export'))


@dataclass(frozen=True)
class Issue:
    field: str
    code: str
    indicator: str


class NotReady(ValueError):
    """An operation was asked for while its readiness checks fail."""

    def __init__(self, issues):
        self.issues = tuple(issues)
        super().__init__(', '.join(issue.code for issue in self.issues))


@dataclass(frozen=True)
class Readiness:
    issues: tuple[Issue, ...]

    @property
    def ready(self) -> bool:
        return not self.issues


def readiness(config: Configuration, indicator: str, purpose: str) -> Readiness:
    if indicator not in ('a', 'b') or purpose not in PURPOSES:
        raise ValueError('Unknown indicator or purpose')
    issues = []

    def issue(field, code):
        issues.append(Issue(field, code, indicator))

    selected = getattr(config, indicator)
    evidence = selected.evidence
    if not selected.asset:
        issue('asset', 'asset_required')
    if config.workflow not in tuple(Workflow):
        issue('workflow', 'invalid_workflow')
    if config.workflow == Workflow.CUSTOM_CANONICAL and selected.asset == config.default_asset:
        issue('asset', 'default_raw_asset')
    if not evidence or evidence.status != 'ready' or not evidence.classes or not evidence.images:
        issue('classes', 'discovery_required')
    elif evidence.asset != selected.asset or evidence.aoi_identity != config.aoi_identity:
        issue('classes', 'stale_discovery')
    elif purpose != 'setup' and any(image.asset and image.asset not in evidence.images
                                    for image in selected.images):
        # Year rows are checked by the outputs, not by the land-cover step; empty rows
        # are reported as years_required below.
        issue('images', 'stale_images')

    targets = set(selected.targets)
    def valid_codes(codes):
        return all(type(code) is int for code in codes)

    if evidence and (not valid_codes(evidence.classes)
                     or len(set(evidence.classes)) != len(evidence.classes)):
        issue('classes', 'invalid_discovery')
    if not targets or not valid_codes(targets) or len(targets) != len(selected.targets):
        issue('targets', 'invalid_targets')
    if indicator == 'a' and not targets <= set(range(1, 11)):
        issue('targets', 'unknown_target')
    if indicator == 'b' and (not valid_codes(targets) or any(not 1 <= code <= 99 for code in targets)):
        issue('targets', 'transition_code_range')

    mapping = dict(selected.mapping)
    if len(mapping) != len(selected.mapping) or not valid_codes(mapping) or not valid_codes(mapping.values()):
        issue('mapping', 'invalid_mapping')
    if config.workflow != Workflow.CUSTOM_CANONICAL:
        # The packaged mapping cannot be edited; as legacy no_remap, classes it lacks are masked.
        user_mapping = config.workflow == Workflow.CUSTOM_RECLASSIFY
        if not mapping or (user_mapping and evidence and not set(evidence.classes) <= set(mapping)):
            issue('mapping', 'mapping_incomplete')
        if any(code in (0, 999) for code in mapping.values()):
            issue('mapping', 'mapping_unassigned')
        if set(mapping.values()) - targets:
            issue('mapping', 'unknown_target')
        effective = {mapping[code] for code in evidence.classes if code in mapping} if evidence else set()
    else:
        if mapping:
            issue('mapping', 'unexpected_mapping')
        effective = set(evidence.classes) if evidence else set()
        if effective - targets:
            issue('classes', 'unknown_target')

    if indicator == 'b':
        table = config.transition
        explicit = config.workflow == Workflow.CUSTOM_RECLASSIFY
        if not table or (explicit and (not table.explicitly_selected or not table.source)):
            issue('transition', 'transition_required')
        else:
            pairs = [(source, target) for source, target, _ in table.rows]
            if (not table.content_digest or len(pairs) != len(set(pairs))
                or any(not valid_codes(row) or row[2] not in (1, 2, 3)
                       or row[0] not in targets or row[1] not in targets for row in table.rows)
                or not set(product(effective, repeat=2)) <= set(pairs)):
                issue('transition', 'invalid_transition')

    if purpose != 'setup':
        if not config.aoi_identity:
            issue('aoi', 'aoi_required')
        images = selected.images
        valid_years = bool(images) and all(image.asset and type(image.year) is int and image.year > 0 for image in images)
        if not valid_years:
            issue('images', 'years_required')
        if indicator == 'b' and (len(images) < 3 or (valid_years and any(left.year >= right.year for left, right in zip(images, images[1:])))):
            issue('images', 'period_order')
        if indicator == 'a' and purpose in ('statistics', 'chart') and valid_years:
            if not all(type(year) is int and year > 0 for year in config.reporting_intervals):
                issue('images', 'invalid_reporting_schedule')
            else:
                try:
                    if not reporting_breakpoints(images, config.reporting_intervals):
                        issue('images', 'no_reporting_years')
                except ValueError:
                    issue('images', 'duplicate_years')
        scale = config.scale
        if not ((scale.mode == 'native' and scale.metres is None) or
                (scale.mode == 'custom' and type(scale.metres) is int and 10 <= scale.metres <= 1500)):
            issue('scale', 'scale_range')
        if purpose in ('statistics', 'chart') and config.rsa and not config.dem:
            issue('dem', 'dem_required')
        if config.units not in ('sqkm', 'ha') or (purpose in ('statistics', 'chart') and config.units != 'sqkm'):
            issue('units', 'invalid_units')
    return Readiness(tuple(issues))
