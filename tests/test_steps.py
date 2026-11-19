import ipyvuetify as v
import pysepal
import pytest
import solara
from packaging.version import Version
from pysepal.solara.components.map_app import MapApp

from component.message import msg
from component.scripts.steps import add_step_actions

STEPS = [
    {"id": 2, "display": "dialog", "content": "area of interest"},
    {"id": 3, "display": "dialog", "content": "land cover"},
    {"id": 4, "display": "dialog", "content": "indicator settings"},
    {"id": 5, "display": "dialog", "content": [], "right_panel_action": "toggle"},
    {"id": 6, "display": "dialog", "content": "export from task"},
]

CLOSE = {"label": msg('app.step_action.close'), "close": True, "cancel": True}


def next_to(step_id):
    return {"label": msg('app.step_action.next'), "next": step_id}


def back_to(step_id):
    return {"label": msg('app.step_action.back'), "next": step_id, "cancel": True}


def test_each_step_window_can_be_closed_and_moves_back_and_forth():
    steps = add_step_actions(STEPS)

    assert [step.get("actions") for step in steps] == [
        [CLOSE, next_to(3)],
        [CLOSE, back_to(2), next_to(4)],
        [CLOSE, back_to(3), next_to(5)],
        None,
        # "Back" skips "4. Results", which has no window.
        [CLOSE, back_to(4)],
    ]


def test_the_steps_given_are_not_changed():
    add_step_actions(STEPS)

    assert all("actions" not in step for step in STEPS)


def walk(widget):
    yield widget
    children = list(getattr(widget, "children", ()) or ())
    for slot in getattr(widget, "v_slots", None) or []:
        slot_children = slot.get("children")
        children += slot_children if isinstance(slot_children, list) else [slot_children]
    for child in children:
        if child is not None and not isinstance(child, str):
            yield from walk(child)


@pytest.fixture
def shell():
    """Render the MapApp shell with a settings window and the results step."""
    contexts = []

    def render(panel_open=False):
        current = []
        box, context = solara.render(
            MapApp(
                main_map=[v.Html(tag="div")],
                steps_data=add_step_actions(
                    [
                        {"id": 4, "name": "Settings", "display": "dialog", "content": [v.Html(tag="div")]},
                        {"id": 5, "name": "Results", "display": "dialog", "content": [],
                         "right_panel_action": "toggle"},
                    ]
                ),
                right_panel_config={"title": "Results"},
                right_panel_content=[{"title": "A", "content": [v.Html(tag="div")]}],
                right_panel_open=panel_open,
                on_current_step=current.append,
            ),
            handle_error=False,
        )
        contexts.append(context)
        return box, current

    yield render
    for context in contexts:
        context.close()


def open_step(box, step_id):
    item = next(w for w in walk(box) if hasattr(w, "vue_click")
                and (w.item_attributes or {}).get("data-step-id") == str(step_id))
    item.vue_click(None)


def step_window(box):
    return next(w for w in walk(box) if isinstance(w, v.Dialog) and "sepal-mapapp__dialog" in (w.content_class or ""))


def press(box, label):
    button = next(w for w in walk(step_window(box)) if isinstance(w, v.Btn) and label in (w.children or []))
    button.fire_event("click", None)


def results_panel_open(box):
    return any("sepal-right-panel--open" in (getattr(w, "class_", None) or "").split() for w in walk(box))


def test_next_to_the_results_step_opens_the_results_panel_and_no_window(shell):
    box, current = shell()
    open_step(box, 4)

    press(box, msg('app.step_action.next'))

    assert step_window(box).v_model is False
    assert current[-1] is None
    if not results_panel_open(box) and Version(pysepal.__version__) < Version("4.2.1"):
        pytest.skip("pysepal < 4.2.1 closes the window but opens no panel (openforis/pysepal#1126)")
    assert results_panel_open(box)


def test_next_to_the_results_step_keeps_an_open_results_panel_open(shell):
    box, _ = shell(panel_open=True)
    open_step(box, 4)

    press(box, msg('app.step_action.next'))

    assert results_panel_open(box)


def test_other_steps_open_their_window(shell):
    box, current = shell()

    open_step(box, 4)

    assert step_window(box).v_model is True
    assert current == [4]
