"""Floating map legend driven by the per-session LegendRegistry."""

from dataclasses import asdict

import solara

from pysepal.solara.components.legend import LegendComponent

from component.scripts.legend import LegendRegistry, resolve_legend_view


@solara.component
def MapLegend(registry: LegendRegistry):
    """Render the active layer's legend, with a dropdown to switch layers.

    Reads the reactive registry (subscribing this component to its changes) and
    feeds the resolved view into pysepal's LegendComponent. Renders nothing when
    no layer on the map has a legend.
    """
    entries = registry.entries.value
    selected = registry.selected.value

    data, options, effective = resolve_legend_view(entries, selected)
    if data is None:
        return

    LegendComponent(
        legend_data=asdict(data),
        selector_options=options if len(options) > 1 else None,
        selected=effective,
        event_set_selected=registry.selected.set,
    )
