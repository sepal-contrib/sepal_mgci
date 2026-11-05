"""The app shell: pysepal's MapApp, with a "Next" that can open the results panel."""

from pysepal.sepalwidgets.vue_app import MapApp

from component.scripts.steps import opens_panel_only


class MgciMapApp(MapApp):
    """MapApp whose "Next" to a step without a window opens the panel of that step.

    MapApp shows the window of the step that a "Next" button activates, but
    "4. Results" has no window: it opens the results panel.
    """

    def vue_handle_step_activation(self, step_id):
        step = next((step for step in self.steps_data if step["id"] == step_id), None)
        if step is not None and opens_panel_only(step):
            # "open", not the step's own "toggle": "Next" must not close an open panel.
            self.vue_handle_right_panel_action("open")
            return
        super().vue_handle_step_activation(step_id)
