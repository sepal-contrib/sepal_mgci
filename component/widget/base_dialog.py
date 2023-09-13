import sepal_ui.sepalwidgets as sw
import ipyvuetify as v


class BaseDialog(v.Dialog):
    def __init__(self, title: str, action_text: str, content: list, *args, **kwargs):
        kwargs["persistent"] = kwargs.get("persistent", False)
        kwargs["v_model"] = kwargs.get("v_model", False)
        kwargs["max_width"] = 750
        kwargs["overlay_opacity"] = 0.7

        super().__init__(*args, **kwargs)

        self.action_btn = sw.Btn(msg=action_text, small=True, color="secondary")
        self.cancel_btn = sw.Btn(msg="Cancel", small=True, color="secondary")
        actions = sw.CardActions(
            children=[
                v.Spacer(),
                self.cancel_btn,
                self.action_btn,
            ]
        )

        self.children = [
            sw.Card(
                class_="pa-2",
                children=[
                    sw.CardTitle(children=title),
                    sw.CardText(children=content),
                    actions,
                ],
            ),
        ]

    def open_dialog(self, *_):
        """Call vegetation view build and open the dialog."""

        self.v_model = True

    def close_dialog(self, *_):
        """Close dialog."""
        self.v_model = False
