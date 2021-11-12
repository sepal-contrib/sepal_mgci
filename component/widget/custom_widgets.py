from traitlets import link, CBool, Int
import ipyvuetify as v
import sepal_ui.sepalwidgets as sw

__all__ = ["BoolQuestion", "Tabs"]


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
        self.dark = True

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
            )
        ]

        self.children = self.tabs + self.content

        link((self.tabs[0], "v_model"), (self.content[0], "v_model"))

        super().__init__(**kwargs)
