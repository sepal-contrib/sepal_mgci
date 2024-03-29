from traitlets import CBool, Unicode, link, observe
from sepal_ui import sepalwidgets as sw

import component.widget.custom_widgets as cw
from component.message import cm


class Questionnaire(sw.Layout):
    """Vegetation questionnaire widget.

    Do some questions to the user, save the answers
    in the traits and use them later to display the proper Vegetation View
    """

    ans_custom_lulc = CBool().tag(sync=True)
    "bool: answer Would you like to use a custom land use/land cover map?"

    ans_transition_matrix = CBool().tag(sync=True)
    "bool: answer do you have a custom land cover transition matrix (.csv)?"

    indicator = Unicode().tag(sync=True)

    def __init__(self) -> sw.Layout:
        self.class_ = "d-block"

        super().__init__()

        # Set widget questions
        self.wq_custom_lulc = cw.BoolQuestion(cm.veg_layer.questionnaire.q1)
        self.wq_transition_matrix = cw.BoolQuestion(cm.veg_layer.questionnaire.q2)

        description = sw.Markdown(cm.veg_layer.description)

        self.children = [
            sw.CardText(
                children=[
                    description,
                    self.wq_custom_lulc,
                    self.wq_transition_matrix,
                ]
            )
        ]

        link((self.wq_custom_lulc, "v_model"), (self, "ans_custom_lulc"))
        link((self.wq_transition_matrix, "v_model"), (self, "ans_transition_matrix"))

    @observe("ans_custom_lulc")
    def toggle_question(self, change):
        """Toggle second question, based on the first answer"""

        if change["new"]:
            self.wq_transition_matrix.hide()
        else:
            self.wq_transition_matrix.show()
