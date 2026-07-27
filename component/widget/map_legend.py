"""Floating map legend for thematic layers.

A ``VuetifyTemplate`` wrapper around pysepal's ``Legend.vue`` that owns an ordered
registry of layer legends. ``register``/``clear`` update it from GEE task threads;
``resolve_legend_view`` maps the registry to the template's props.
"""

import threading
from dataclasses import asdict
from pathlib import Path

import ipyvuetify as v
import solara
import traitlets as t

from pysepal.solara.components import legend as _pysepal_legend
from pysepal.solara.components.legend import LegendData

from component.scripts.legend import BIOBELT_KEY, LegendEntry, resolve_legend_view

# Reuse pysepal's Legend.vue verbatim (ships next to its legend.py).
_LEGEND_VUE = str(Path(_pysepal_legend.__file__).parent / "Legend.vue")


class MapLegendWidget(v.VuetifyTemplate):
    """ipyvuetify legend overlay reusing pysepal's Legend.vue."""

    template_file = t.Unicode(_LEGEND_VUE).tag(sync=True)

    legend_data = t.Dict(default_value={}).tag(sync=True)
    visible = t.Bool(True).tag(sync=True)
    collapsed = t.Bool(False).tag(sync=True)
    selector_options = t.List(default_value=[]).tag(sync=True)
    selected = t.Unicode(default_value=None, allow_none=True).tag(sync=True)

    def __init__(self, **kwargs):
        self._entries: "dict[str, LegendEntry]" = {}
        self._lock = threading.Lock()
        super().__init__(**kwargs)

    def register(self, key: str, title: str, data: LegendData) -> None:
        """Add/replace a layer's legend and show it."""
        with self._lock:
            self._entries[key] = LegendEntry(title=title, data=data)
            self._apply(key)

    def clear(self) -> None:
        """Drop every legend (e.g. on AOI change)."""
        with self._lock:
            self._entries = {}
            self._apply(None)

    def clear_thematic(self, keep=(BIOBELT_KEY,)) -> None:
        """Drop thematic legends, keeping the biobelt one; reselect what remains."""
        keep = set(keep)
        with self._lock:
            self._entries = {k: e for k, e in self._entries.items() if k in keep}
            self._apply(self.selected)

    def vue_set_selected(self, value: str) -> None:
        """Frontend dropdown picked a layer."""
        with self._lock:
            self._apply(value)

    def _apply(self, selected_hint) -> None:
        data, options, effective = resolve_legend_view(self._entries, selected_hint)
        self.legend_data = asdict(data) if data is not None else {}
        self.selector_options = options
        self.selected = effective


@solara.component
def MapLegend(map_):
    """Mount the map's legend widget (created in ``MgciMap``) as a floating overlay."""
    solara.display(map_.legend)
