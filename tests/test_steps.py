import ipyvuetify as v

from component.message import msg
from component.scripts.steps import add_step_actions
from component.widget.app_shell import MgciMapApp

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
        # "4. Results" opens the results panel, not a window: close this one first.
        [CLOSE, back_to(3), {**next_to(5), "close": True}],
        None,
        # "Back" skips "4. Results", which has no window.
        [CLOSE, back_to(4)],
    ]


def test_the_steps_given_are_not_changed():
    add_step_actions(STEPS)

    assert all("actions" not in step for step in STEPS)


def shell():
    return MgciMapApp(
        steps_data=add_step_actions(
            [
                {
                    "id": 4,
                    "name": "Settings",
                    "display": "dialog",
                    "content": [v.Html(tag="div")],
                },
                {
                    "id": 5,
                    "name": "Results",
                    "display": "dialog",
                    "content": [],
                    "right_panel_action": "toggle",
                },
            ]
        ),
        right_panel_config={"title": "Results"},
        right_panel_content=[{"title": "A", "content": [v.Html(tag="div")]}],
    )


def click_next_to_results(app):
    """What the browser does for a "Next" with "close": close the window, then activate."""
    app.vue_handle_step_deactivation()
    app.vue_handle_step_activation(5)


def test_next_to_the_results_step_opens_the_results_panel_and_no_window():
    app = shell()
    app.vue_handle_step_activation(4)

    click_next_to_results(app)

    assert app.right_panel_open is True
    assert app.step_open is False
    assert app.current_step is None


def test_next_to_the_results_step_keeps_an_open_results_panel_open():
    app = shell()
    app.right_panel[0].is_open = True
    app.vue_handle_step_activation(4)

    click_next_to_results(app)

    assert app.right_panel_open is True


def test_other_steps_open_their_window():
    app = shell()

    app.vue_handle_step_activation(4)

    assert app.step_open is True
    assert app.current_step == 4
