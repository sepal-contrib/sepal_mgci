"""Canonical values; adapters normalize raw input before constructing these."""

from dataclasses import dataclass, fields
from enum import Enum


class Workflow(str, Enum):
    DEFAULT = 'default'
    DEFAULT_EDIT_TRANSITIONS = 'default_edit_transitions'
    CUSTOM_RECLASSIFY = 'custom_reclassify'
    CUSTOM_CANONICAL = 'custom_canonical'

    # Not StrEnum: the SEPAL app image and CI run Python 3.10. This keeps StrEnum's str().
    def __str__(self):
        return self.value


class Immutable:
    def __post_init__(self):
        def check(value):
            if isinstance(value, tuple):
                for item in value:
                    check(item)
            elif not isinstance(value, (str, int, float, bool, type(None), Immutable)):
                raise TypeError(f'Configuration contains mutable or unsupported {type(value).__name__}')
        for field in fields(self):
            check(getattr(self, field.name))


@dataclass(frozen=True)
class ScalePolicy(Immutable):
    mode: str = 'native'
    metres: int | None = None


@dataclass(frozen=True)
class ImageSelection(Immutable):
    asset: str
    year: int


@dataclass(frozen=True)
class DatasetEvidence(Immutable):
    asset: str
    images: tuple[str, ...]
    classes: tuple[int, ...]
    aoi_identity: str
    status: str = 'empty'
    version: str = ''


@dataclass(frozen=True)
class IndicatorConfig(Immutable):
    asset: str
    evidence: DatasetEvidence | None = None
    mapping: tuple[tuple[int, int], ...] = ()
    targets: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
    images: tuple[ImageSelection, ...] = ()
    labels: tuple[tuple[int, str, str], ...] = ()


@dataclass(frozen=True)
class TransitionTable(Immutable):
    rows: tuple[tuple[int, int, int], ...]
    source: str
    content_digest: str
    explicitly_selected: bool = False
    schema_version: str = '1'


@dataclass(frozen=True)
class Configuration(Immutable):
    aoi_identity: str
    workflow: Workflow
    a: IndicatorConfig
    b: IndicatorConfig
    transition: TransitionTable | None = None
    scale: ScalePolicy = ScalePolicy()
    rsa: bool = False
    dem: str = 'CGIAR/SRTM90_V4'
    source: str = 'Food and Agriculture Organization of United Nations (FAO)'
    default_asset: str = 'users/amitghosh/sdg_module/esa/cci_landcover'
    biobelt: str = 'users/xavidelamo/SDG1542_Mntn_BioclimaticBelts'
    algorithm_version: str = '1'
    units: str = 'sqkm'
    aoi_graph: str = ''
    aoi_name: str = ''
    # AOI short name (e.g. ISO code) used in report folder and file names.
    aoi_label: str = ''
    ref_area: str = ''
    reporting_intervals: tuple[int, ...] = (2000, 2005, 2010, 2015, 2018, 2021, 2024)


@dataclass(frozen=True)
class DatasetDiscovery(Immutable):
    evidence: DatasetEvidence
    images: tuple[ImageSelection, ...]
