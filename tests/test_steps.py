from component.message import cm
from component.scripts.steps import add_step_actions

STEPS = [
    {"id": 2, "display": "dialog", "content": "area of interest"},
    {"id": 3, "display": "dialog", "content": "land cover"},
    {"id": 4, "display": "dialog", "content": "indicator settings"},
    {"id": 5, "display": "dialog", "content": [], "right_panel_action": "toggle"},
    {"id": 6, "display": "dialog", "content": "export from task"},
]

CLOSE = {"label": cm.app.step_action.close, "close": True, "cancel": True}


def next_to(step_id):
    return {"label": cm.app.step_action.next, "next": step_id}


def test_each_step_window_can_be_closed_and_opens_the_next_step_window():
    steps = add_step_actions(STEPS)

    assert [step.get("actions") for step in steps] == [
        [CLOSE, next_to(3)],
        [CLOSE, next_to(4)],
        # "4. Results" opens the results panel, not a window.
        [CLOSE],
        None,
        [CLOSE],
    ]


def test_the_steps_given_are_not_changed():
    add_step_actions(STEPS)

    assert all("actions" not in step for step in STEPS)
