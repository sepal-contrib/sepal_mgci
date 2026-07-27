"""Legend entry type and the pure view resolver for the map legend."""

from dataclasses import dataclass

from pysepal.solara.components.legend import LegendData

BIOBELT_KEY = "biobelt"


@dataclass
class LegendEntry:
    """A registered layer legend: a display title and its serializable data."""

    title: str
    data: LegendData


def resolve_legend_view(entries: dict, selected):
    """Pure resolver → ``(legend_data | None, selector_options, effective_selected)``.

    Falls back to the last entry when ``selected`` was pruned; returns
    ``(None, [], None)`` when empty.
    """
    if not entries:
        return None, [], None
    keys = list(entries)
    effective = selected if selected in entries else keys[-1]
    options = [{"value": k, "text": entries[k].title} for k in keys]
    return entries[effective].data, options, effective
