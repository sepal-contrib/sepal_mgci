"""Reporting-year selection from a captured schedule and source dates."""

from .configuration import ImageSelection


def reporting_breakpoints(images: tuple[ImageSelection, ...], intervals: tuple[int, ...]):
    by_year = {image.year: image for image in images}
    if len(by_year) != len(images):
        raise ValueError('Each source year must identify one image')
    result = []
    for year in sorted(set(intervals)):
        if year in by_year:
            result.append((year, (by_year[year],)))
        else:
            before = max((value for value in by_year if value < year), default=None)
            after = min((value for value in by_year if value > year), default=None)
            if before is not None and after is not None:
                result.append((year, (by_year[before], by_year[after])))
    return tuple(result)
