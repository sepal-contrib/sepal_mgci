from pathlib import Path
from typing import Dict, List, NewType, Tuple, TypedDict, Union

Pathlike = Union[str, Path]
"""A type hint for a path-like object, either a string or a Path object."""


# Output from reduce regions


class Group(TypedDict):
    lc: int
    sum: float


class SubItem(TypedDict):
    biobelt: int
    groups: List[Group]


class SubAYearDict(TypedDict):
    sub_a: List[SubItem]


class SubBYearDict(TypedDict):
    baseline_degradation: List[SubItem]
    baseline_transition: List[SubItem]
    final_degradation: List[SubItem]
    report_transition: List[SubItem]


YearKey = NewType("YearKey", str)
"""YearKey can be either 'singleYear'(sub_A) or 'year__year__year' (sub_B)."""

ResultsDict = Dict[YearKey, Union[SubAYearDict, SubBYearDict]]
"""A dictionary containing the results of the calculation for subindicators A and/or B."""
