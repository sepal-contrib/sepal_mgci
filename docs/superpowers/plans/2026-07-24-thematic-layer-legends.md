# Unified Map Legend for Thematic Layers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show a legend for every thematic map layer (Sub-A land cover, Sub-B degradation, land-cover maps) alongside the bioclimatic belts, unified onto pysepal's Solara `LegendComponent` with a dropdown to switch between the layers currently on the map.

**Architecture:** Extend pysepal's shared `LegendComponent` with optional per-item `detail` text and an optional layer selector. In sepal_mgci, a per-session `LegendRegistry` (backed by `solara.reactive`) is attached to the map; the classic widgets (`AoiView`, `LayerHandler`) write layer legends into it, and one thin Solara `MapLegend` component reads it and renders the pysepal legend. The old classic bottom-right `LegendControl` is removed.

**Tech Stack:** Python 3.10, Solara, ipyvuetify/Vue (`component_vue`), pandas, pytest. Two repos on two branches (see Global Constraints).

## Global Constraints

- **pysepal repo:** `/home/dguerrero/1_modules/pysepal`, branch `feat/legend-detail-selector`. Tasks 1–2 only.
- **sepal_mgci worktree:** `/home/dguerrero/1_modules/sepal_mgci-worktrees/thematic-legends`, branch `feat/thematic-layer-legends`. Tasks 3–8.
- The sepal_mgci env imports pysepal editable from `/home/dguerrero/1_modules/pysepal`, so pysepal Tasks 1–2 must land before sepal_mgci Tasks 3–8 (which use `DiscreteEntry(detail=...)` and the selector props).
- **Python interpreter for all test commands:** `~/micromamba/envs/sepal_mgci/bin/python` (the only env with pysepal + solara + pytest). Run pysepal tests from the pysepal repo dir, sepal_mgci tests from the worktree dir.
- **Commit messages:** short subject line, no body padding. **Do NOT add any `Co-Authored-By` or "Generated with Claude" trailer** (user's standing rule).
- Vue-rendered output (detail text, chip-skip, vertical stacking, dropdown) is verified **in-browser**, not unit-tested — `component_vue` renders on the frontend and erases the Python signature.
- Backward compatibility: existing `LegendComponent` / `DiscreteEntry` callers pass nothing new; all additions are optional with defaults.

---

## Task 1: pysepal — `DiscreteEntry.detail` field

**Files:**
- Modify: `pysepal/solara/components/legend.py`
- Test: `tests/test_solara/test_legend.py` (create)

**Interfaces:**
- Produces: `DiscreteEntry(label: str, color: str, detail: str = "")` — sepal_mgci builders (Task 3) rely on the `detail` keyword and on `color=""` being valid.

- [ ] **Step 1: Write the failing test**

Create `tests/test_solara/test_legend.py`:

```python
"""Tests for the reusable Solara map legend dataclasses."""

from dataclasses import asdict

from pysepal.solara.components.legend import DiscreteEntry, LegendData


def test_discrete_entry_detail_defaults_empty():
    entry = DiscreteEntry(label="Forest", color="#006400")
    assert entry.detail == ""


def test_discrete_entry_detail_roundtrips_through_asdict():
    entry = DiscreteEntry(label="Nival", color="#ff0000", detail="1,234 km² · 12%")
    assert asdict(entry) == {
        "label": "Nival",
        "color": "#ff0000",
        "detail": "1,234 km² · 12%",
    }


def test_legend_data_serializes_items_with_detail_and_empty_color():
    data = LegendData(items=[DiscreteEntry("Total", "", detail="9,999 km² · 100%")])
    payload = asdict(data)
    assert payload["items"][0]["color"] == ""
    assert payload["items"][0]["detail"] == "9,999 km² · 100%"
    assert payload["gradients"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/1_modules/pysepal && ~/micromamba/envs/sepal_mgci/bin/python -m pytest tests/test_solara/test_legend.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'detail'`.

- [ ] **Step 3: Add the field**

In `pysepal/solara/components/legend.py`, change the `DiscreteEntry` dataclass:

```python
@dataclass
class DiscreteEntry:
    """A single labeled color chip."""

    label: str
    color: str
    detail: str = ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/1_modules/pysepal && ~/micromamba/envs/sepal_mgci/bin/python -m pytest tests/test_solara/test_legend.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
cd ~/1_modules/pysepal
git add pysepal/solara/components/legend.py tests/test_solara/test_legend.py
git commit -m "feat(legend): add optional detail text to DiscreteEntry"
```

---

## Task 2: pysepal — Legend.vue detail rendering + layer selector

**Files:**
- Modify: `pysepal/solara/components/legend.py` (extend `LegendComponent` signature)
- Modify: `pysepal/solara/components/Legend.vue`

**Interfaces:**
- Produces: `LegendComponent(..., selector_options: Optional[list] = None, selected: Optional[str] = None, event_set_selected: Optional[Callable[[str], None]] = None)`. `selector_options` items are `{"value": str, "text": str}`. When `selector_options` has ≥2 entries a `<select>` renders; the Vue method `set_selected(value)` is invoked on change. `MapLegend` (Task 5) relies on these names.

- [ ] **Step 1: Extend the Python signature**

In `pysepal/solara/components/legend.py`, replace the `LegendComponent` definition with:

```python
@solara.component_vue("Legend.vue")
def LegendComponent(
    legend_data: Optional[dict] = None,
    visible: bool = True,
    collapsed: bool = False,
    event_set_collapsed: Optional[Callable[[bool], None]] = None,
    selector_options: Optional[list] = None,
    selected: Optional[str] = None,
    event_set_selected: Optional[Callable[[str], None]] = None,
):
    """Floating map legend overlay.

    Renders at bottom-center of the viewport over the map area.
    Supports gradient bars and discrete color chips.

    Args:
        legend_data: Serialized LegendData (use dataclasses.asdict).
            Empty dict or missing keys = nothing rendered.
        visible: Show/hide the entire legend.
        collapsed: Collapsed state (icon pill only).
        event_set_collapsed: Callback when user toggles collapse.
        selector_options: Optional [{"value", "text"}] layer options. When two
            or more are given, a compact dropdown renders at the top of the
            legend body; one or none renders no dropdown.
        selected: The currently selected option value.
        event_set_selected: Callback when the user picks a different option.
    """
    pass
```

- [ ] **Step 2: Update the Vue template — chip-skip, detail, stacking, selector**

In `pysepal/solara/components/Legend.vue`, inside `<template>`, replace the discrete-items block:

```html
      <!-- Discrete items -->
      <div v-if="parsedItems.length > 0" class="sepal-legend__items">
        <div
          v-for="(item, ii) in parsedItems"
          :key="'i-' + ii"
          class="sepal-legend__item"
        >
          <span
            class="sepal-legend__chip"
            :style="{ backgroundColor: item.color }"
          ></span>
          <span class="sepal-legend__label">{{ item.label }}</span>
        </div>
      </div>
```

with:

```html
      <!-- Discrete items -->
      <div
        v-if="parsedItems.length > 0"
        class="sepal-legend__items"
        :class="{ 'sepal-legend__items--detailed': hasDetail }"
      >
        <div
          v-for="(item, ii) in parsedItems"
          :key="'i-' + ii"
          class="sepal-legend__item"
        >
          <span
            v-if="item.color"
            class="sepal-legend__chip"
            :style="{ backgroundColor: item.color }"
          ></span>
          <span class="sepal-legend__label">{{ item.label }}</span>
          <span v-if="item.detail" class="sepal-legend__detail">{{
            item.detail
          }}</span>
        </div>
      </div>
```

Then, still inside `<div class="sepal-legend__body">`, add the selector as the **first** child (immediately after the opening `<div v-if="!isCollapsed" class="sepal-legend__body">` line):

```html
      <!-- Layer selector (only with 2+ options) -->
      <div v-if="showSelector" class="sepal-legend__selector">
        <select
          class="sepal-legend__select"
          :value="selected"
          @change="onSelect($event)"
          aria-label="Choose which layer legend to show"
        >
          <option
            v-for="(opt, oi) in selector_options"
            :key="'o-' + oi"
            :value="opt.value"
          >
            {{ opt.text }}
          </option>
        </select>
      </div>
```

- [ ] **Step 3: Update the Vue script — props, computed, method**

In the `<script>` `props` object, add after `collapsed`:

```js
    selector_options: {
      type: Array,
      default: () => [],
    },
    selected: {
      type: String,
      default: null,
    },
```

In `computed`, add:

```js
    hasDetail() {
      return this.parsedItems.some(function (it) {
        return it.detail;
      });
    },
    showSelector() {
      return (
        Array.isArray(this.selector_options) &&
        this.selector_options.length > 1
      );
    },
```

In `methods`, add after `toggleCollapse`:

```js
    onSelect(e) {
      var val = e && e.target ? e.target.value : null;
      if (val != null && typeof this.set_selected === "function") {
        this.set_selected(val);
      }
    },
```

- [ ] **Step 4: Update the Vue styles — detail + selector, theme-aware**

In the scoped `<style>` block, after the `.sepal-legend__item` rule, add:

```css
.sepal-legend__items--detailed {
  flex-direction: column;
  align-items: stretch;
  flex-wrap: nowrap;
  gap: 3px;
  align-self: stretch;
}
.sepal-legend__items--detailed .sepal-legend__item {
  justify-content: flex-start;
}
.sepal-legend__detail {
  margin-left: auto;
  padding-left: 14px;
  opacity: 0.7;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.sepal-legend__selector {
  align-self: stretch;
}
.sepal-legend__select {
  width: 100%;
  font-family: inherit;
  font-size: 12px;
  padding: 3px 6px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  color: inherit;
  cursor: pointer;
}
.sepal-legend--dark .sepal-legend__select {
  border-color: rgba(255, 255, 255, 0.25);
  background: rgba(255, 255, 255, 0.06);
}
.sepal-legend--light .sepal-legend__select {
  border-color: rgba(0, 0, 0, 0.2);
  background: rgba(0, 0, 0, 0.03);
}
```

- [ ] **Step 5: Regression check — existing legend tests still pass**

Run: `cd ~/1_modules/pysepal && ~/micromamba/envs/sepal_mgci/bin/python -m pytest tests/test_solara/test_legend.py tests/test_mapping/test_LegendControl.py -v`
Expected: PASS (Task 1 tests still green; the classic control is untouched).

- [ ] **Step 6: Browser verification (manual)**

The Vue rendering cannot be unit-tested. When the sepal_mgci app is running (after Task 8), confirm in-browser:
- Biobelt legend shows one row per belt with `label` on the left and muted `area km² · %` on the right; the "Total" row has **no** color chip.
- Land-cover / degradation legends show wrapped color chips (no detail).
- With ≥2 layers on the map a dropdown appears at the top of the legend and switches the shown legend; with one layer there is no dropdown.
- Both light and dark themes render legibly.

- [ ] **Step 7: Commit**

```bash
cd ~/1_modules/pysepal
git add pysepal/solara/components/legend.py pysepal/solara/components/Legend.vue
git commit -m "feat(legend): render item detail and optional layer selector"
```

---

## Task 3: sepal_mgci — legend-data builders

**Files:**
- Modify: `component/parameter/visualization.py`
- Test: `tests/test_scripts/test_legend.py` (create)

**Interfaces:**
- Consumes: `LegendData`, `DiscreteEntry` from `pysepal.solara.components.legend` (Task 1); `LEGENDS` (already in this module); `cm.aoi.legend.*` column names.
- Produces: `land_cover_legend_data() -> LegendData`, `degradation_legend_data() -> LegendData`, `biobelt_legend_data(df) -> LegendData`. Tasks 6 and 7 import these.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_scripts/test_legend.py`:

```python
"""Tests for legend-data builders and the per-session legend registry."""

import pandas as pd

from component.message import cm
from component.parameter.visualization import (
    biobelt_legend_data,
    degradation_legend_data,
    land_cover_legend_data,
)
from pysepal.solara.components.legend import LegendData


def _biobelt_df():
    return pd.DataFrame(
        {
            cm.aoi.legend.color: ["#ff0000", "#034502", "#24221f"],
            cm.aoi.legend.desc: [
                "Nival",
                "Remaining mountain area",
                cm.aoi.legend.total,
            ],
            cm.aoi.legend.area: ["1,234", "5,000", "6,234"],
            cm.aoi.legend.perc: ["19.8", "80.2", "100.0"],
        }
    )


def test_land_cover_legend_data_has_ten_items_without_detail():
    data = land_cover_legend_data()
    assert isinstance(data, LegendData)
    assert len(data.items) == 10
    assert data.items[0].detail == ""


def test_degradation_legend_data_labels():
    data = degradation_legend_data()
    assert [i.label for i in data.items] == ["Degraded", "Stable", "Improved"]


def test_biobelt_legend_data_detail_and_chipless_total():
    data = biobelt_legend_data(_biobelt_df())
    nival = data.items[0]
    assert nival.color == "#ff0000"
    assert nival.detail == "1,234 km² · 19.8%"
    total = data.items[-1]
    assert total.label == cm.aoi.legend.total
    assert total.color == ""
    assert total.detail == "6,234 km² · 100.0%"


def test_biobelt_legend_data_no_mountain_has_no_detail():
    df = pd.DataFrame(
        {
            cm.aoi.legend.color: ["gray"],
            cm.aoi.legend.desc: ["No mountain"],
            cm.aoi.legend.area: ["0"],
            cm.aoi.legend.perc: ["0"],
        }
    )
    assert biobelt_legend_data(df).items[0].detail == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/1_modules/sepal_mgci-worktrees/thematic-legends && ~/micromamba/envs/sepal_mgci/bin/python -m pytest tests/test_scripts/test_legend.py -v`
Expected: FAIL — `ImportError: cannot import name 'biobelt_legend_data'`.

- [ ] **Step 3: Add the builders**

In `component/parameter/visualization.py`, add at the top (after the existing imports):

```python
from component.message import cm
from pysepal.solara.components.legend import DiscreteEntry, LegendData
```

and at the end of the file:

```python
def land_cover_legend_data() -> LegendData:
    """Discrete chips for the land-cover classes."""
    return LegendData(
        items=[
            DiscreteEntry(label=label, color=color)
            for label, color in LEGENDS["land_cover"].items()
        ]
    )


def degradation_legend_data() -> LegendData:
    """Discrete chips for the degradation classes."""
    return LegendData(
        items=[
            DiscreteEntry(label=label, color=color)
            for label, color in LEGENDS["degradation"].items()
        ]
    )


def biobelt_legend_data(df) -> LegendData:
    """Build the biobelt legend from the area DataFrame returned by get_belt_area.

    ``df`` columns are the renamed ``cm.aoi.legend.*`` labels
    (Color / Description / Area (sqkm) / %). The "Total" row is rendered without
    a color chip; rows with no real area (the no-mountain fallback) carry no
    detail text.
    """
    total_label = cm.aoi.legend.total
    items = []
    for _, row in df.iterrows():
        label = row[cm.aoi.legend.desc]
        area = row[cm.aoi.legend.area]
        perc = row[cm.aoi.legend.perc]
        detail = "" if area in ("-", "0") else f"{area} km² · {perc}%"
        color = "" if label == total_label else row[cm.aoi.legend.color]
        items.append(DiscreteEntry(label=label, color=color, detail=detail))
    return LegendData(items=items)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/1_modules/sepal_mgci-worktrees/thematic-legends && ~/micromamba/envs/sepal_mgci/bin/python -m pytest tests/test_scripts/test_legend.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
cd ~/1_modules/sepal_mgci-worktrees/thematic-legends
git add component/parameter/visualization.py tests/test_scripts/test_legend.py
git commit -m "feat: add legend-data builders for thematic layers"
```

---

## Task 4: sepal_mgci — `LegendRegistry` + `resolve_legend_view`

**Files:**
- Create: `component/scripts/legend.py`
- Test: `tests/test_scripts/test_legend.py` (append)

**Interfaces:**
- Consumes: `solara.reactive`; `LegendData` from pysepal.
- Produces:
  - `BIOBELT_KEY: str = "biobelt"`
  - `LegendEntry(title: str, data: LegendData)` (dataclass)
  - `LegendRegistry` with `.entries` (reactive `dict[str, LegendEntry]`), `.selected` (reactive `str | None`), `.register(key, title, data)`, `.unregister(key)`, `.clear()`, `.clear_thematic(keep=(BIOBELT_KEY,))`
  - `resolve_legend_view(entries, selected) -> (LegendData | None, list[dict], str | None)`
  - Tasks 5–8 consume all of these.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_scripts/test_legend.py`:

```python
from component.scripts.legend import (
    BIOBELT_KEY,
    LegendEntry,
    LegendRegistry,
    resolve_legend_view,
)


def test_register_appends_and_auto_selects():
    reg = LegendRegistry()
    reg.register("land_cover_2020", "Land cover 2020", LegendData())
    assert list(reg.entries.value) == ["land_cover_2020"]
    assert reg.selected.value == "land_cover_2020"


def test_register_same_key_dedupes_and_keeps_order():
    reg = LegendRegistry()
    reg.register("a", "A", LegendData())
    reg.register("b", "B", LegendData())
    reg.register("a", "A2", LegendData())
    assert list(reg.entries.value) == ["a", "b"]
    assert reg.entries.value["a"].title == "A2"
    assert reg.selected.value == "a"


def test_clear_empties_everything():
    reg = LegendRegistry()
    reg.register("a", "A", LegendData())
    reg.clear()
    assert reg.entries.value == {}
    assert reg.selected.value is None


def test_clear_thematic_keeps_biobelt():
    reg = LegendRegistry()
    reg.register(BIOBELT_KEY, "Bioclimatic belts", LegendData())
    reg.register("land_cover_2020", "Land cover 2020", LegendData())
    reg.clear_thematic()
    assert list(reg.entries.value) == [BIOBELT_KEY]
    assert reg.selected.value == BIOBELT_KEY


def test_unregister_updates_selection():
    reg = LegendRegistry()
    reg.register("a", "A", LegendData())
    reg.register("b", "B", LegendData())
    reg.unregister("b")
    assert list(reg.entries.value) == ["a"]
    assert reg.selected.value == "a"


def test_resolve_empty_returns_none():
    assert resolve_legend_view({}, None) == (None, [], None)


def test_resolve_builds_options_and_effective():
    entries = {
        "a": LegendEntry("A", LegendData()),
        "b": LegendEntry("B", LegendData()),
    }
    data, options, effective = resolve_legend_view(entries, "b")
    assert options == [
        {"value": "a", "text": "A"},
        {"value": "b", "text": "B"},
    ]
    assert effective == "b"
    assert data is entries["b"].data


def test_resolve_falls_back_when_selected_missing():
    entries = {"a": LegendEntry("A", LegendData())}
    _, _, effective = resolve_legend_view(entries, "gone")
    assert effective == "a"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/1_modules/sepal_mgci-worktrees/thematic-legends && ~/micromamba/envs/sepal_mgci/bin/python -m pytest tests/test_scripts/test_legend.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'component.scripts.legend'`.

- [ ] **Step 3: Create the module**

Create `component/scripts/legend.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/1_modules/sepal_mgci-worktrees/thematic-legends && ~/micromamba/envs/sepal_mgci/bin/python -m pytest tests/test_scripts/test_legend.py -v`
Expected: PASS (12 passed — 4 from Task 3 + 8 here).

- [ ] **Step 5: Commit**

```bash
cd ~/1_modules/sepal_mgci-worktrees/thematic-legends
git add component/scripts/legend.py tests/test_scripts/test_legend.py
git commit -m "feat: add per-session LegendRegistry and view resolver"
```

---

## Task 5: sepal_mgci — `MapLegend` Solara component

**Files:**
- Create: `component/widget/map_legend.py`

**Interfaces:**
- Consumes: `LegendRegistry`, `resolve_legend_view` (Task 4); `LegendComponent` (Task 2); `dataclasses.asdict`.
- Produces: `MapLegend(registry: LegendRegistry)` Solara component. Task 8 mounts it in `Page()`.

- [ ] **Step 1: Create the component**

Create `component/widget/map_legend.py`:

```python
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
```

- [ ] **Step 2: Import smoke check**

Run:
```bash
cd ~/1_modules/sepal_mgci-worktrees/thematic-legends
~/micromamba/envs/sepal_mgci/bin/python -c "from component.widget.map_legend import MapLegend; print('MapLegend import OK')" 2>&1 | grep -iv "html object\|javascript object\|futurewarning\|warnings.warn" | tail -1
```
Expected: `MapLegend import OK`.

- [ ] **Step 3: Commit**

```bash
cd ~/1_modules/sepal_mgci-worktrees/thematic-legends
git add component/widget/map_legend.py
git commit -m "feat: add MapLegend Solara component"
```

---

## Task 6: sepal_mgci — wire `LayerHandler` (map.py)

**Files:**
- Modify: `component/widget/map.py`

**Interfaces:**
- Consumes: `land_cover_legend_data`, `degradation_legend_data` (Task 3); `map_.legend_registry` (attached in Task 8).
- Produces: on `add_layer_async`, registers the added layer under `selection[2]`; on `update_layer_list`, prunes thematic legends.

- [ ] **Step 1: Swap the legend import and drop the commented block**

In `component/widget/map.py`, replace the import line:

```python
from component.widget.legend_control import LegendDashboard
```

with:

```python
from component.parameter.visualization import (
    degradation_legend_data,
    land_cover_legend_data,
)
```

In `LayerHandler.__init__`, delete the commented-out block:

```python
        # self.map_.add_legend(
        #     "lc_legend", "Land cover", visuals.LEGENDS["land_cover"], vertical=False
        # )
        # self.map_.add_legend(
        #     "deg_legend", "Degradation", visuals.LEGENDS["degradation"]
        # )
```

- [ ] **Step 2: Prune thematic legends on layer-list change**

In `LayerHandler.update_layer_list`, immediately after:

```python
        self.map_.remove_all(keep_names=["AOI", cm.aoi.legend.belts])
```

add:

```python
        self.map_.legend_registry.clear_thematic()
```

- [ ] **Step 3: Register the layer legend on add**

In `LayerHandler.add_layer_async`, set `legend_data` inside each branch. Change the `if selection[0] == "a":` branch to:

```python
        if selection[0] == "a":
            remap_matrix = self.model.matrix_sub_a
            layer, vis_params = get_layer_a(selection[1], remap_matrix, aoi)
            legend_data = land_cover_legend_data()
```

and the `elif selection[0] == "b":` branch to:

```python
        elif selection[0] == "b":
            remap_matrix = self.model.matrix_sub_b
            sub_b_year = self.model.sub_b_year
            transition_matrix = self.model.transition_matrix

            layer, vis_params = get_layer_b(
                selection[1], remap_matrix, aoi, sub_b_year, transition_matrix
            )
            legend_data = (
                degradation_legend_data()
                if "degradation" in selection[1]
                else land_cover_legend_data()
            )
```

Then, at the end of the method, after:

```python
        await self.map_.add_ee_layer_async(
            layer, vis_params=vis_params, name=selection[2]
        )
```

add:

```python
        self.map_.legend_registry.register(selection[2], selection[2], legend_data)
```

- [ ] **Step 4: Remove the dead `Map.add_legend` method**

In `component/widget/map.py`, delete the entire `add_legend` method from the `Map` class (the method starting `def add_legend(` through its `return self.add(self.legend)`), since it depended on the now-removed `LegendDashboard`. Leave the rest of the `Map` class unchanged.

- [ ] **Step 5: Import smoke check**

Run:
```bash
cd ~/1_modules/sepal_mgci-worktrees/thematic-legends
~/micromamba/envs/sepal_mgci/bin/python -c "import component.widget.map; print('map.py import OK')" 2>&1 | grep -iv "html object\|javascript object\|futurewarning\|warnings.warn" | tail -1
```
Expected: `map.py import OK` (no ImportError for `LegendDashboard`).

- [ ] **Step 6: Commit**

```bash
cd ~/1_modules/sepal_mgci-worktrees/thematic-legends
git add component/widget/map.py
git commit -m "feat: register thematic-layer legends from LayerHandler"
```

---

## Task 7: sepal_mgci — wire `AoiView` biobelt legend (aoi_tile.py)

**Files:**
- Modify: `component/tile/aoi_tile.py`

**Interfaces:**
- Consumes: `BIOBELT_KEY` (Task 4), `biobelt_legend_data` (Task 3), `map_.legend_registry` (Task 8), `cm.aoi.legend.belts`, `self.alert`.
- Produces: biobelt legend registered under `BIOBELT_KEY`; registry cleared on AOI change.

- [ ] **Step 1: Fix imports**

In `component/tile/aoi_tile.py`:
- Delete **both** occurrences of `from component.widget.legend_control import LegendControl` (there are two).
- Delete `from copy import deepcopy` (only used by the code removed below).
- Add:

```python
from component.scripts.legend import BIOBELT_KEY
from component.parameter.visualization import biobelt_legend_data
```

- [ ] **Step 2: Remove the classic legend control from `__init__`**

In `AoiView.__init__`, delete:

```python
        if self.map_:  # for debugging
            self.map_.legend = LegendControl({}, title="", position="bottomright")
            self.map_.add_control(self.map_.legend)
```

- [ ] **Step 3: Register the biobelt legend in `get_belt_map`**

Replace the whole body of `get_belt_map` with:

```python
    async def get_belt_map(self):

        biobelt_layer = self.map_.add_ee_layer_async(
            ee.Image(BIOBELT).clip(self.model.feature_collection),
            name=cm.aoi.legend.belts,
            vis_params=BIOBELT_VIS,
        )

        belt_area = get_belt_area(self.model.feature_collection, ee.Image(BIOBELT))

        coros = [biobelt_layer, belt_area]

        try:
            biobelt_layer, belt_area = await asyncio.gather(*coros)
            _, df = belt_area

            self.map_.legend_registry.register(
                BIOBELT_KEY, cm.aoi.legend.belts, biobelt_legend_data(df)
            )

            self.alert.add_msg(ms.aoi_sel.complete, "success")

        except Exception as e:
            self.alert.add_msg(f"Failed to get biobelt map: {e}", "error")
```

- [ ] **Step 4: Clear the registry on AOI change**

In `AoiView._update_aoi`, replace:

```python
                self.map_.legend.hide()
```

with:

```python
                self.map_.legend_registry.clear()
```

- [ ] **Step 5: Import smoke check**

Run:
```bash
cd ~/1_modules/sepal_mgci-worktrees/thematic-legends
~/micromamba/envs/sepal_mgci/bin/python -c "import component.tile.aoi_tile; print('aoi_tile.py import OK')" 2>&1 | grep -iv "html object\|javascript object\|futurewarning\|warnings.warn" | tail -1
```
Expected: `aoi_tile.py import OK`.

- [ ] **Step 6: Commit**

```bash
cd ~/1_modules/sepal_mgci-worktrees/thematic-legends
git add component/tile/aoi_tile.py
git commit -m "feat: register biobelt legend via LegendRegistry"
```

---

## Task 8: sepal_mgci — mount, delete dead code, integration check

**Files:**
- Modify: `solara_app.py`
- Delete: `component/widget/legend_control.py`

**Interfaces:**
- Consumes: `LegendRegistry` (Task 4), `MapLegend` (Task 5).
- Produces: the registry attached to the map and the legend mounted in `Page()`.

- [ ] **Step 1: Import the registry and component**

In `solara_app.py`, add near the other component imports:

```python
from component.scripts.legend import LegendRegistry
from component.widget.map_legend import MapLegend
```

- [ ] **Step 2: Attach the registry to the map**

In `Page()`, change:

```python
    map_ = MgciMap(gee_interface=gee_interface, theme_toggle=theme_toggle)
    aoi_view = AoiView(map_=map_)
```

to:

```python
    map_ = MgciMap(gee_interface=gee_interface, theme_toggle=theme_toggle)
    map_.legend_registry = LegendRegistry()
    aoi_view = AoiView(map_=map_)
```

- [ ] **Step 3: Mount the legend**

In `Page()`, immediately before the `MapApp.element(` call, add:

```python
    MapLegend(map_.legend_registry)

```

- [ ] **Step 4: Delete the classic legend module**

```bash
cd ~/1_modules/sepal_mgci-worktrees/thematic-legends
git rm component/widget/legend_control.py
```

- [ ] **Step 5: Grep for stragglers**

Run:
```bash
cd ~/1_modules/sepal_mgci-worktrees/thematic-legends
grep -rn "legend_control\|LegendDashboard\|LegendControl\|\.legend\b\|add_legend" --include="*.py" component/ solara_app.py
```
Expected: no references to `legend_control`, `LegendDashboard`, `LegendControl`, `add_legend`, or `self.map_.legend` (only `legend_registry` / `MapLegend` / message keys like `cm.aoi.legend.*` remain). Fix any straggler before continuing.

- [ ] **Step 6: Run the new test suite + changed-module imports**

Run:
```bash
cd ~/1_modules/sepal_mgci-worktrees/thematic-legends
~/micromamba/envs/sepal_mgci/bin/python -m pytest tests/test_scripts/test_legend.py -v
~/micromamba/envs/sepal_mgci/bin/python -c "import solara_app; print('solara_app import OK')" 2>&1 | grep -iv "html object\|javascript object\|futurewarning\|warnings.warn" | tail -1
```
Expected: 12 passed; `solara_app import OK`.
(If `import solara_app` needs live GEE/network and fails on `init_ee()`, fall back to importing the changed modules individually: `component.widget.map`, `component.tile.aoi_tile`, `component.widget.map_legend`, `component.scripts.legend`, `component.parameter.visualization`.)

- [ ] **Step 7: Browser end-to-end verification (manual)**

Launch the app and confirm the whole flow:
- Select an AOI → biobelt legend appears bottom-center with per-belt `area km² · %` and a chip-less Total row; no dropdown yet.
- Add a Sub-A land-cover layer → its 10-class chip legend shows; a dropdown now lists *Bioclimatic belts* + *Land cover …*; switching the dropdown swaps the shown legend.
- Add a Sub-B degradation layer → Degraded/Stable/Improved chips; dropdown lists all three.
- Re-add the same layer → no duplicate dropdown entry.
- Change the subindicator years (triggers `remove_all`) → thematic entries drop, biobelt stays.
- Pick a new AOI → legend clears, then re-populates with the new biobelt.
- Toggle dark/light theme → legend stays legible.

- [ ] **Step 8: Commit**

```bash
cd ~/1_modules/sepal_mgci-worktrees/thematic-legends
git add solara_app.py component/widget/legend_control.py
git commit -m "feat: mount unified map legend and remove classic LegendControl (#81)"
```

---

## Self-Review Notes

**Spec coverage:**
- pysepal `DiscreteEntry.detail` → Task 1. Legend.vue detail/chip-skip/stacking + selector → Task 2.
- `LegendRegistry` (register/unregister/clear/clear_thematic) → Task 4. `MapLegend` → Task 5. Builders → Task 3.
- `LayerHandler` wiring → Task 6. `AoiView` wiring (register / clear / alert-routed errors) → Task 7. Mount + removals → Task 8.
- Data flow (classic widgets write reactive registry → MapLegend reads) → Tasks 4–8.
- Edge cases: no-mountain/Total (Task 3 tests); selected-pruned fallback (Task 4 `resolve` test); dedupe (Task 4 test); modal-hidden legend (pre-existing Vue rule, unchanged).
- Out of scope honored: dropdown does not toggle layer visibility; no gradient legends; no other tiles touched.

**Deviation from spec:** the spec's pysepal "render-tree smoke test" is replaced by browser verification (Task 2 Step 6) because `component_vue` renders on the frontend and hides its signature — a Python mount test would assert nothing meaningful. MapLegend's logic is fully covered by the pure `resolve_legend_view` tests (Task 4).

**Type consistency:** `register(key, title, data)`, `LegendEntry(title, data)`, `resolve_legend_view(entries, selected) -> (data, options, effective)`, and `selector_options=[{"value","text"}]` are used identically across Tasks 4–8 and match the pysepal `LegendComponent` props from Task 2.
