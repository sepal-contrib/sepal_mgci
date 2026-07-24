"""Per-session registry of map-layer legends and its pure view resolver."""

from dataclasses import dataclass

import solara

from pysepal.solara.components.legend import LegendData

BIOBELT_KEY = "biobelt"


@dataclass
class LegendEntry:
    """A registered layer legend: a display title and its serializable data."""

    title: str
    data: LegendData


class LegendRegistry:
    """Ordered, per-session registry of layer legends backed by solara reactives.

    Keyed by a stable layer key (also the ee-layer name for thematic layers, so
    re-adding a layer dedupes). ``register`` auto-selects the new key.
    """

    def __init__(self):
        self.entries = solara.reactive({})  # dict[str, LegendEntry], insertion-ordered
        self.selected = solara.reactive(None)  # currently displayed key

    def register(self, key: str, title: str, data: LegendData) -> None:
        entries = dict(self.entries.value)
        entries[key] = LegendEntry(title=title, data=data)
        self.entries.value = entries
        self.selected.value = key

    def unregister(self, key: str) -> None:
        entries = dict(self.entries.value)
        entries.pop(key, None)
        self.entries.value = entries
        if self.selected.value not in entries:
            self.selected.value = next(reversed(entries), None)

    def clear(self) -> None:
        self.entries.value = {}
        self.selected.value = None

    def clear_thematic(self, keep=(BIOBELT_KEY,)) -> None:
        keep = set(keep)
        entries = {k: v for k, v in self.entries.value.items() if k in keep}
        self.entries.value = entries
        if self.selected.value not in entries:
            self.selected.value = next(reversed(entries), None)


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
