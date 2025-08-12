import ipyvuetify as v
from sepal_ui import color
import sepal_ui.sepalwidgets as sw
from sepal_ui.frontend.resize_trigger import rt
from traitlets import CBool, Int, link
from ipyvuetify import Btn


__all__ = ["BoolQuestion", "Tabs", "TaskMsg", "Alert"]


class BoolQuestion(v.Flex, sw.SepalWidget):
    v_model = CBool(False).tag(sync=True)

    def __init__(self, question, *args, **kwargs):
        super().__init__(*args, **kwargs)

        bool_radios = v.RadioGroup(
            row=True,
            v_model=self.v_model,
            children=[
                v.Radio(label="No", value=False),
                v.Radio(label="Yes", value=True),
            ],
        )

        link((bool_radios, "v_model"), (self, "v_model"))

        self.children = [v.Html(tag="h3", children=[question]), bool_radios]


class Tabs(v.Card):
    current = Int(0).tag(sync=True)

    def __init__(self, titles, content, **kwargs):
        self.background_color = "primary"
        self.dark = True if color._dark_theme else False

        self.tabs = [
            v.Tabs(
                v_model=self.current,
                children=[
                    v.Tab(children=[title], key=key) for key, title in enumerate(titles)
                ],
            )
        ]

        self.content = [
            v.TabsItems(
                v_model=self.current,
                children=[
                    v.TabItem(children=[content], key=key)
                    for key, content in enumerate(content)
                ],
            ),
        ]

        self.children = self.tabs + self.content  # + [rt]

        link((self.tabs[0], "v_model"), (self.content[0], "v_model"))

        super().__init__(**kwargs)

        # self.content[0].observe(lambda *_: rt.resize(), "v_model")


class Alert(sw.Alert):
    def set_state(self, state_color, id_: int = 1):
        """sets a state (color) to the icon of the TaskMsg component"""

        if self.get_children(attr="id", value=f"task_msg_{id_}"):
            task_msg = self.get_children(attr="id", value=f"task_msg_{id_}")[0]
            task_msg.set_state(state_color)
            return

    def set_msg(self, msg: str, id_: int = 1):
        if id_:
            if self.get_children(attr="id", value=f"task_msg_{id_}"):
                task_msg = self.get_children(attr="id", value=f"task_msg_{id_}")[0]
                task_msg.set_msg(msg)
                return self

            # If not found, create a new one
            task_msg = TaskMsg(msg, id_)

        return super().append_msg(msg=task_msg)


class TaskMsg(sw.Flex):
    colors = ["info", "success", "error", "warning"]

    def __init__(self, msg: str, id_: int):
        super().__init__()

        self.attributes = {"id": f"task_msg_{id_}"}

        self.class_ = "d-flex"
        self.icon = sw.Icon(children=["mdi-circle"], color="info")

        self.children = [msg, v.Spacer(), self.icon]

    def set_msg(self, msg):
        """mutate and set new message by replacing"""

        self.children = [msg] + self.children[1:]

    def set_state(self, state_color):
        """sets a state (color) to the icon"""

        if state_color not in self.colors:
            raise Exception(f"Invalid color, use {self.colors}")

        if state_color == "success":
            self.icon.children = ["mdi-checkbox-marked-circle"]
        elif state_color == "warning":
            self.icon.children = ["mdi-information"]

        self.icon.color = state_color


class AlertDialog(sw.Dialog):
    def __init__(self, w_alert: sw.Alert):
        self.max_width = 750
        self.persistent = True
        self.style_ = "margin: 0 !important;"

        super().__init__()

        self.v_model = False
        self.w_alert = w_alert

        btn_close = Btn(
            block=True,
            children=["Close"],
        )
        self.children = [
            sw.Card(
                class_="pt-4",
                children=[
                    self.w_alert,
                    sw.CardActions(children=[btn_close]),
                ],
            )
        ]
        btn_close.on_event("click", lambda *_: setattr(self, "v_model", False))
        self.w_alert.observe(self.open_dialog, "children")

    def open_dialog(self, change):
        """Opens the dialog when there's a change in the alert chilndren state."""
        if change["new"] != [""]:
            self.v_model = True
