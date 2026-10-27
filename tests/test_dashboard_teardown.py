"""Dashboard views close the widgets a render or a switch replaces, and only those."""

import ipyvuetify as v
import ipywidgets
import pandas as pd
import pytest
from ipecharts.baseechartswidget import BaseEchartsWidget
from ipecharts.option.basewidget import BaseWidget as EChartsOptionWidget
from pysepal.solara.theme import ThemeState

from component.scripts.plots import (
    get_land_cover_bar_chart,
    get_sankey_chart,
    get_transition_matrix_chart,
)
from component.widget.mgci_dashboard import DashboardRequestSelector
from tests.test_dashboard_view import make_case


@pytest.fixture(params=["a", "b"])
def case(request, monkeypatch):
    return make_case(request.param, monkeypatch)


def switch_belt_and_view(case):
    """Use the in-dialog controls that replace chart content without a request."""
    view = case.view
    if case.kind == "a":
        view.mgci_dashboard.select_belt(2)
        view.mgci_dashboard.select_belt("Total")
    else:
        view.belt_selector.select(2)
        view.select_view("matrix")
        view.belt_selector.select("Total")
        view.select_view("flow")


def model_tree(root):
    """Every widget model shown under ``root``: children, chart options and layouts."""
    found = {}

    def visit(value):
        if isinstance(value, (list, tuple)):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            for item in value.values():
                visit(item)
        elif isinstance(value, ipywidgets.Widget) and id(value) not in found:
            found[id(value)] = value
            visit(getattr(value, "children", None) or [])
            if isinstance(value, BaseEchartsWidget):
                visit(value.option)
                visit(value.layout)
            if isinstance(value, EChartsOptionWidget):
                visit([getattr(value, name) for name in value.keys])

    visit(root)
    return found


def open_names(widgets):
    return [type(widget).__name__ for widget in widgets if widget.comm is not None]


def closed_names(widgets):
    return [type(widget).__name__ for widget in widgets if widget.comm is None]


def test_rerender_closes_what_it_replaced(case):
    view = case.view
    view.render_dashboard((case.selections[0], case.data))
    before = model_tree(view)

    view.render_dashboard((case.selections[1], case.data))
    after = model_tree(view)

    replaced = [widget for key, widget in before.items() if key not in after]
    assert replaced
    assert open_names(replaced) == []
    assert closed_names(after.values()) == []


def test_reused_widgets_stay_open_across_renders_and_switches(case):
    view = case.view
    reused = [view.btn, view.alert, view.results_dialog, case.selector]
    if case.kind == "b":
        reused += [
            view.view_selector,
            view.flow_button,
            view.matrix_button,
            view.chart_host,
            view.matrix_hint,
            view.impact_legend,
        ]

    view.render_dashboard((case.selections[0], case.data))
    switch_belt_and_view(case)
    view.render_dashboard((case.selections[1], case.data))
    switch_belt_and_view(case)

    current = [view.btn, view.alert, view.results_dialog, case.selector]
    if case.kind == "b":
        current += [
            view.view_selector,
            view.flow_button,
            view.matrix_button,
            view.chart_host,
            view.matrix_hint,
            view.impact_legend,
        ]
    assert all(old is new for old, new in zip(reused, current))
    widgets = [w for root in reused for w in model_tree(root).values()]
    assert closed_names(widgets) == []


def test_widgets_close_only_after_leaving_the_display(case, monkeypatch):
    view = case.view
    early = []
    close = ipywidgets.Widget.close

    def checked_close(widget):
        if widget.comm is not None and id(widget) in model_tree(view):
            early.append(type(widget).__name__)
        close(widget)

    monkeypatch.setattr(ipywidgets.Widget, "close", checked_close)

    view.render_dashboard((case.selections[0], case.data))
    switch_belt_and_view(case)
    view.render_dashboard((case.selections[1], case.data))
    switch_belt_and_view(case)

    assert early == []


def test_a_belt_switch_closes_the_previous_chart_models(monkeypatch):
    case = make_case("a", monkeypatch)
    case.view.render_dashboard((2020, case.data))
    dashboard = case.view.mgci_dashboard
    previous = model_tree(dashboard.chart)

    dashboard.select_belt(2)

    assert open_names(previous.values()) == []
    assert closed_names(model_tree(dashboard).values()) == []


def test_b_view_and_belt_switches_close_only_the_replaced_chart_content(monkeypatch):
    case = make_case("b", monkeypatch)
    view = case.view
    view.render_dashboard((case.selections[1], case.data))
    class_key = view.class_key
    seen = {}

    for switch in (
        lambda: view.belt_selector.select(2),
        lambda: view.select_view("matrix"),
        lambda: view.belt_selector.select("Total"),
        lambda: view.select_view("flow"),
        lambda: view.select_view("matrix"),
    ):
        seen.update(model_tree(view))
        switch()
        shown = model_tree(view)
        kept = {
            **model_tree(view.matrix_hint),
            **model_tree(view.impact_legend),
            **model_tree(view.class_key),
        }
        stays = [w for key, w in seen.items() if key in shown or key in kept]
        gone = [w for key, w in seen.items() if key not in shown and key not in kept]
        assert closed_names(stays) == []
        assert open_names(gone) == []

    assert view.class_key is class_key
    assert view.chart_host.children[3] is class_key


def test_b_rerender_closes_the_previous_class_key_while_it_is_hidden(monkeypatch):
    case = make_case("b", monkeypatch)
    view = case.view
    view.render_dashboard((case.selections[1], case.data))
    previous = model_tree(view.class_key)

    view.render_dashboard((case.selections[0], case.data))

    assert open_names(previous.values()) == []
    assert view.class_key.comm is not None


def test_request_selector_closes_replaced_buttons():
    selector = DashboardRequestSelector(on_request=lambda value: None)
    selector.set_choices([(1, "1", 1), (2, "2", 2)])
    previous = list(selector.buttons.values())

    selector.set_choices([(2, "2", 2), (3, "3", 3)])

    assert open_names(previous) == []
    assert closed_names(selector.buttons.values()) == []
    assert selector.children == list(selector.buttons.values())


@pytest.mark.parametrize(
    "make_chart",
    [
        lambda state: get_sankey_chart(theme_state=state)[1],
        lambda state: get_land_cover_bar_chart(
            pd.DataFrame({"lc_class": [1], "sum": [25.0]}),
            {1: ["Forest", "#123456"]},
            theme_state=state,
        ),
        lambda state: get_transition_matrix_chart(
            pd.DataFrame({"from_lc": [1], "to_lc": [2], "sum": [4.0]}),
            theme_state=state,
        ),
    ],
    ids=["sankey", "bar", "matrix"],
)
def test_closing_a_chart_closes_its_option_models(make_chart):
    chart = make_chart(ThemeState(mode="light"))
    models = model_tree(chart)
    assert len(models) > 1

    chart.close()

    assert open_names(models.values()) == []


def test_close_tree_closes_descendants_but_not_kept_subtrees():
    from component.widget.mgci_dashboard import close_tree

    kept_child = v.Html(tag="span", children=["kept"])
    kept = v.Flex(children=[kept_child])
    leaf = v.Html(tag="span", children=["text"])
    _, chart = get_sankey_chart(theme_state=ThemeState(mode="light"))
    chart_models = model_tree(chart)
    root = v.Flex(children=[v.Card(children=[leaf, "plain text"]), kept, chart])
    shared = root._jupyter_vue

    close_tree(root, keep=[kept])

    assert root.comm is None
    assert leaf.comm is None
    assert open_names(chart_models.values()) == []
    assert kept.comm is not None
    assert kept_child.comm is not None
    assert shared.comm is not None


def test_close_tree_leaves_a_kept_root_open():
    from component.widget.mgci_dashboard import close_tree

    child = v.Html(tag="span")
    root = v.Flex(children=[child])

    close_tree(root, keep=[root])

    assert root.comm is not None
    assert child.comm is not None
