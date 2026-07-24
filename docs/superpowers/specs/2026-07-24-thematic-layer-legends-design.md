# Unified map legend for thematic layers (#81)

## Problem

The map legend only ever shows the bioclimatic belts. When a user displays any
other layer from the right-panel **Visualize and export layers** section —
Sub-indicator A land cover, Sub-indicator B degradation, or land-cover maps —
no legend explains the colors. Issue #81 asks for legends for those layers.

Today there is a single classic ipyleaflet `LegendControl` widget-control
anchored bottom-right, driven only by the biobelt area computation in
`AoiView`. `LayerHandler.add_layer_async` adds thematic layers to the map but
registers no legend (the original intent survives as commented-out
`add_legend("lc_legend", ...)` / `add_legend("deg_legend", ...)` calls).

## Decision summary

- **Unify** every map legend onto pysepal's Solara `LegendComponent` (bottom-
  center, theme-aware, collapsible). The classic bottom-right `LegendControl`
  is removed.
- A single legend is shown at a time, defaulting to the **last-added** layer.
  A compact **dropdown** on the legend lets the user switch between all layers
  currently on the map that have a legend. The dropdown only appears when there
  are ≥2 such layers.
- The biobelt's per-belt **area (km²)** and **%** are preserved by adding an
  optional `detail` field to pysepal's `DiscreteEntry`, rendered as muted
  secondary text.

## pysepal changes (`feat/legend-detail-selector`)

These extend the shared, reusable `LegendComponent`; they are backward-
compatible (existing callers pass nothing new).

### 1. `DiscreteEntry.detail`

`pysepal/solara/components/legend.py`:

```python
@dataclass
class DiscreteEntry:
    label: str
    color: str
    detail: str = ""   # NEW — muted secondary text, e.g. "1,234 km² · 12%"
```

`Legend.vue`:
- Render `item.detail` as a muted span after the label.
- Skip the color chip when `item.color` is empty (`v-if="item.color"`) — used
  by the biobelt "Total" row, which has no meaningful color box.
- When **any** item in the legend has a non-empty `detail`, lay the discrete
  items out vertically (one per row) instead of the default wrapped row, so the
  `label · detail` pairs read as a list. Legends without detail (land cover,
  degradation) keep the existing wrapped-chip layout.

### 2. Optional layer selector

`LegendComponent` gains three optional props:

```python
@solara.component_vue("Legend.vue")
def LegendComponent(
    legend_data: Optional[dict] = None,
    visible: bool = True,
    collapsed: bool = False,
    event_set_collapsed: Optional[Callable[[bool], None]] = None,
    selector_options: Optional[list] = None,   # NEW — [{"value": str, "text": str}, ...]
    selected: Optional[str] = None,            # NEW — currently selected value
    event_set_selected: Optional[Callable[[str], None]] = None,  # NEW
):
```

`Legend.vue`:
- When `selector_options` has ≥2 entries, render a compact native `<select>` at
  the top of the legend body, styled to match the overlay (small, theme-aware).
  Its `@change` calls `this.set_selected(value)` (mirrors the existing
  `event_set_collapsed` → `set_collapsed` convention).
- ≤1 option → no dropdown (identical to current rendering).
- The component stays presentational: it reports selection intent via the event
  and renders whatever `legend_data` it is handed. Selection state lives in the
  caller (`MapLegend`).

### 3. pysepal tests

Extend the existing legend test module: assert `DiscreteEntry(detail=...)`
survives `asdict`, and that `LegendComponent` mounts with the new props (render-
tree smoke test). Vue-rendered detail/dropdown output is verified in-browser,
not unit-tested (frontend rendering).

## sepal_mgci changes (`feat/thematic-layer-legends`)

### 4. `LegendRegistry` (per-session state)

New module `component/scripts/legend.py` (pure-ish, holds Solara reactives):

```python
class LegendRegistry:
    """Per-session ordered registry of layer legends, backed by solara reactives."""
    def __init__(self):
        self.entries = solara.reactive({})    # ordered {name: LegendData}
        self.selected = solara.reactive(None)  # currently displayed name

    def register(self, name: str, legend_data: LegendData) -> None:
        # replace-or-append (dedupes same-named layers); auto-selects `name`
    def unregister(self, name: str) -> None: ...
    def clear(self) -> None: ...             # AOI change: drop everything
    def clear_thematic(self, keep=(BIOBELT_KEY,)) -> None: ...  # subindicator switch
```

- One instance is created in `Page()` and attached to the map
  (`map_.legend_registry`) so the classic widgets that already hold `self.map_`
  can reach it without extra plumbing.
- Writes replace the whole dict (reactive change detection is by identity).
- Keyed by the layer's **display name** (`selection[2]`, e.g. `"Land cover
  2020"`), which is also the ee-layer name, so re-adding a layer dedupes.

### 5. `MapLegend` Solara component

New `@solara.component` (in `component/widget/map_legend.py`):

- Reads `registry.entries` and `registry.selected` (subscribes).
- Renders nothing when empty.
- Builds `selector_options` from the entry names, resolves the effective
  selected key (falls back to the last entry if the stored selection was
  pruned), and passes `legend_data` / `selector_options` / `selected` into
  pysepal's `LegendComponent`.
- Wires `event_set_selected` → `registry.selected.set`.
- Mounted once in `Page()` alongside `MapApp.element(...)`. Because
  `LegendComponent` is `position: fixed` and positions itself from the CSS
  variables MapApp sets (`--sepal-drawer-width`, `--sepal-right-panel-width`,
  `--sepal-bottom-reserved`), its location in the render tree does not matter.

### 6. Legend-data builders

In `component/parameter/visualization.py` (already the home of `LEGENDS` and
the LC-class CSV), pure functions:

- `land_cover_legend_data() -> LegendData` — discrete chips from
  `LEGENDS["land_cover"]`.
- `degradation_legend_data() -> LegendData` — discrete chips from
  `LEGENDS["degradation"]`.
- `biobelt_legend_data(df) -> LegendData` — from the biobelt area DataFrame:
  one `DiscreteEntry` per row with `detail = f"{area} km² · {perc}%"`; the
  "Total" row gets an empty `color` (no chip). Handles the existing
  "No mountain area" / ZeroDivisionError fallbacks (single entry, no detail).

### 7. Wiring the classic widgets

- `LayerHandler.add_layer_async` (`component/widget/map.py`): after
  `add_ee_layer_async`, register the layer's legend — land-cover vs degradation
  chosen from the selection string (`"degradation" in selection[1]` →
  degradation, else land cover). Remove the commented-out `add_legend` block.
- `LayerHandler.update_layer_list`: where it does
  `remove_all(keep_names=["AOI", belts])`, also call
  `registry.clear_thematic()`.
- `AoiView.get_belt_map` (`component/tile/aoi_tile.py`): replace
  `self.map_.legend.legend_dict = ...` with
  `registry.register(BIOBELT_KEY, biobelt_legend_data(df))`. Route the former
  in-legend loading spinner and `set_error` through the existing `self.alert`
  (success/error already go there). The biobelt ee-layer is still added to the
  map as today.
- `AoiView.__init__`: drop the `map_.legend = LegendControl(...)` /
  `add_control` wiring.
- `AoiView._update_aoi`: replace `self.map_.legend.hide()` with
  `registry.clear()`.

### 8. Removals

Now-dead classic legend code:
- Delete `component/widget/legend_control.py`.
- Delete `Map.add_legend` and `LegendDashboard` from `component/widget/map.py`.
- Drop the corresponding imports.

### 9. sepal_mgci tests

- `biobelt_legend_data` from a sample DataFrame (detail strings, Total row
  chip-less, No-mountain fallback).
- `land_cover_legend_data` / `degradation_legend_data` map colors/labels
  correctly.
- `LegendRegistry`: register auto-selects; re-register same name dedupes;
  `clear_thematic` keeps biobelt; `clear` empties.
- Light render smoke test for `MapLegend` (empty → nothing; one entry → no
  dropdown; two entries → dropdown).

## Data flow

```
AoiView.get_belt_map ─┐
                      ├─► map_.legend_registry (solara.reactive)  ─► MapLegend ─► LegendComponent (Vue)
LayerHandler.add_layer┘        (register / clear / clear_thematic)      ▲
                                                                        │ event_set_selected
                                                            user picks a layer in the dropdown
```

One bottom-center legend. Dropdown lists exactly the layers currently on the
map that carry a legend (≈ the visible thematic content, minus the AOI outline
which has none). The last-added layer is shown by default; the user can switch.

## Edge cases

- **No mountain area / ZeroDivisionError** in biobelt: single fallback entry,
  no detail, no dropdown.
- **Selected layer pruned** (AOI change / subindicator switch): `MapLegend`
  falls back to the last remaining entry, or renders nothing if empty.
- **Same layer re-added**: deduped by name; selection moves to it.
- **Step dialog open**: existing `body.sepal-modal-open .sepal-legend`
  global rule already hides the legend behind modals — unchanged.

## Out of scope

- The dropdown does **not** control map-layer visibility (only which legend is
  shown). Toggling layer visibility from the legend is explicitly deferred.
- No gradient/continuous legends — all current thematic layers are discrete.
- No change to export, calculation, or dashboard tiles.
